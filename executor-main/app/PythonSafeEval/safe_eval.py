import subprocess
from pathlib import Path
import shutil
import os
import shlex
import uuid
import json

class SafeEval:
    def __init__(self, version=None, modules=None, tmp_dir=None):
        self.__module_path = Path(__file__).parent
        while True:
            self.__session_id = "python_safe_eval_" + self.__random_word()
            self.__session_path = self.__module_path / Path('.jailfs') / Path(self.__session_id) if tmp_dir is None else Path(tmp_dir) / Path(self.__session_id)
            if not tmp_dir or not os.path.exists(self.__session_path):
                break

        self.__container_has_started = False
        
        # create .jailfs
        if not (self.__module_path / ".jailfs").is_dir():
            os.mkdir(self.__module_path / ".jailfs")

        # create session path
        if not self.__session_path.is_dir():
            os.mkdir(self.__session_path)
        
        # copy nsjail
        shutil.copytree(self.__module_path / ".nsjail", self.__session_path / ".nsjail")

        # create Dockerfile
        with open(self.__module_path / "Dockerfile_template_python.txt", "r") as f:
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
        result = subprocess.run("""docker run --rm --privileged --name={session_id} -v "{session_path}:/volume" -d -it {session_id}_image""".format(session_id=self.__session_id, session_path=self.__session_path), shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
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

            
    def eval(self, code=None, time_limit=0, scope=None):
        """
        Evaluate code with an optional time limit and an optional scope dict.
        The scope dictionary contains variable names mapped to their values,
        e.g. {"x": 2, "y": 4}.
        """
        if code is None:
            return

        # If no scope is provided, default to empty
        if scope is None:
            scope = {}

        # Build Python lines that define each variable in scope
        # e.g. for {"x": 2, "y": 4}, we produce:
        # x = 2
        # y = 4
        # REPR IS APPARENTLY SAFE TO USE HERE
        scope_definitions = "\n".join(
            f"{var} = {json.dumps(val)};"
            for var, val in scope.items()
        )


        # Combine scope definitions with the actual code
        code_with_scope = scope_definitions + "\n" + code

        # Save code to the volume
        volume_filename = self.__random_word() + ".py"
        with open(self.__session_path / volume_filename, "w+", encoding="utf-8") as f:
            f.write(code_with_scope)

        # Execute file
        return self.__execute_file_in_volume(volume_filename, time_limit)

        # return self.__execute_code_in_memory(code, time_limit)
        
    def __execute_file_in_volume(self, volume_filename, time_limit):
        command = ("docker exec {session_id} nsjail \
            --user 99999 --group 99999 \
            --disable_proc --chroot / --really_quiet \
            --time_limit {time_limit} \
            /usr/bin/python3 /volume/{volume_filename}"\
            ).format(session_id=self.__session_id, time_limit=time_limit, volume_filename=volume_filename)
        
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
print("done")
a = x + 1
y = 1 + y
print(a, y)""", 
    scope={"x": 2, "y": 4},
    time_limit=15))