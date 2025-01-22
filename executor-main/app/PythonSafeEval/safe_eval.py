import subprocess
from pathlib import Path
import shutil
import sys
import os
import random
import string
import shlex
import uuid

class SafeEval:
    def __init__(self, version=None, modules=None, tmp_dir=None):
        self.__module_path = Path(__file__).parent
        while True:
            self.__session_id = "python_safe_eval_" + self.__random_word()
            self.__session_path = self.__module_path / Path('.jailfs') / Path(self.__session_id) if tmp_dir is None else Path(tmp_dir) / Path(self.__session_id)
            if not tmp_dir or not os.path.exists(self.__session_path):
                break

        self.__container_has_started = False
        self.seccomp_path = self.__module_path / "settings/seccomp_profile.json"
        
        # check permission
        if not subprocess.run("git --version", shell=True, capture_output=True).stdout.decode('utf-8').startswith("git version"):
            raise Exception("Git is not installed or have no permission to access.")
        if not subprocess.run("docker ps", shell=True, capture_output=True).stdout.decode('utf-8').startswith("CONTAINER ID"):
            raise Exception("Docker is not installed or have no permission to access.")

        # fetch nsjail
        if not Path(self.__module_path / ".nsjail").is_dir():
            os.mkdir(self.__module_path / ".nsjail")
            
            result = subprocess.run("git clone https://github.com/google/nsjail.git {module_path}/.nsjail".format(module_path=self.__module_path), shell=True, stdout=subprocess.DEVNULL)
            if result.returncode != 0:
                shutil.rmtree(self.__module_path / ".nsjail")
                raise RuntimeError("Failed to clone nsjail, make sure that the internet is connected and the module directory is writable.")
        
        # create .jailfs
        if not (self.__module_path / ".jailfs").is_dir():
            os.mkdir(self.__module_path / ".jailfs")
        


        # create session path
        if not self.__session_path.is_dir():
            os.mkdir(self.__session_path)
        
        # copy nsjail
        shutil.copytree(self.__module_path / ".nsjail", self.__session_path / ".nsjail")

        # create Dockerfile
        with open(self.__module_path / "Dockerfile_template.txt", "r") as f:
            Dockerfile = f.read()
        
        Dockerfile = Dockerfile.format(
            version=version if version is not None else 3, 
            modules="RUN pip3 install " + " ".join(modules) if modules else ""
        )

        with open(self.__session_path / "Dockerfile", "w+") as f:
            f.write(Dockerfile)

        # build docker image
        result = subprocess.run("docker build --network=host -t {session_id}_image .".format(session_id=self.__session_id), shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, cwd=self.__session_path)
        if result.returncode != 0:
            raise RuntimeError("Failed to build docker images: " + result.stderr.decode("utf-8"))

        # run docker image
        result = subprocess.run(
            (
                """docker run --rm --privileged \
                --security-opt seccomp={seccomp_path} \
                --name={session_id} -v "{session_path}:/volume" \
                -d -it {session_id}_image"""
            ).format(
                session_id=self.__session_id, 
                session_path=self.__session_path,
                seccomp_path=self.seccomp_path), 
            shell=True, 
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            raise RuntimeError("Failed to start docker container: " + result.stderr.decode("utf-8"))

        self.__container_has_started = True

    def __del__(self):
        if self.__container_has_started:
            try:
                # stop and remove docker container
                subprocess.run("docker stop {session_id}".format(session_id=self.__session_id).split(), check=True, stdout=subprocess.DEVNULL)

                # remove image 
                subprocess.run("docker image remove {session_id}_image --no-prune".format(session_id=self.__session_id), shell=True, check=True, stdout=subprocess.DEVNULL)
            except:
                pass

        try:
            # remove session directory
            shutil.rmtree(self.__session_path)
        except FileNotFoundError:
            pass

    def eval(self, code=None, time_limit=0):
        if code is None:
            return
        
        # save file to the volume
        volume_filename = self.__random_word() + ".py"
        with open(self.__session_path / volume_filename, "w+") as f:
            f.write(code)
        
        # execute code
        return self.__execute_file_in_volume(volume_filename, time_limit)

        # return self.__execute_code_in_memory(code, time_limit)
        
    def __execute_file_in_volume(self, volume_filename, time_limit):
        command = ("docker exec {session_id} nsjail \
            --user 99999 --group 99999 \
            --disable_proc --chroot / --really_quiet \
            --time_limit {time_limit} \
            /usr/bin/python3 /volume/{volume_filename}"\
            ).format(
                session_id=self.__session_id, 
                time_limit=time_limit, 
                volume_filename=volume_filename,
            )
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Return both stdout and stderr
            return {
                "stdout": result.stdout.decode("utf-8"),
                "stderr": result.stderr.decode("utf-8"),
                "returncode": result.returncode
            }
        except subprocess.CalledProcessError as e:
            return {
                "stdout": e.stdout.decode("utf-8"),
                "stderr": e.stderr.decode("utf-8"),
                "returncode": e.returncode
            }

    def __execute_code_in_memory(self, code_string, time_limit):
        # Safely quote the user code so it doesn't break out of shell
        quoted_code = shlex.quote(code_string)

        command = (
            "docker exec {session_id} nsjail "
            "--user 99999 --group 99999 "
            "--disable_proc --chroot / --really_quiet "
            "--time_limit {time_limit} "
            "/usr/bin/python3 -c {code}"
        ).format(
            session_id=self.__session_id,
            time_limit=time_limit,
            code=quoted_code
        )
        print(f"Debug Command: {command}")
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Return both stdout and stderr
            return {
                "stdout": result.stdout.decode("utf-8"),
                "stderr": result.stderr.decode("utf-8"),
                "returncode": result.returncode
            }
        except subprocess.CalledProcessError as e:
            return {
                "stdout": e.stdout.decode("utf-8"),
                "stderr": e.stderr.decode("utf-8"),
                "returncode": e.returncode
            }

    def __random_word(self):
        # Generate a random UUID
        random_uuid = uuid.uuid4()

        # Convert the UUID to a string
        random_uuid_str = str(random_uuid)
        return random_uuid_str
    

if __name__ == "__main__":
    sf = SafeEval(version="3.8", modules=["setuptools"])
    print(sf.eval(code="""import time
time.sleep(10)
print("done")""", time_limit=15))