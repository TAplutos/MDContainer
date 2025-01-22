import subprocess
import shutil
import uuid
import os
import json
import shlex
from pathlib import Path


class SafeEval:
    """
    Base class that manages:
    1) Creating and cleaning up a temporary session directory
    2) Copying nsjail files
    3) Building and running a Docker container
    4) Providing helper methods to execute commands inside the container via nsjail

    Child classes (e.g. SafeEvalPython, SafeEvalJavaScript) should override:
        - _create_dockerfile()
        - Possibly how code is prepended/written (in their eval() method)
    """
    max_timelimit = 100 # 100 seconds
    def __init__(self, session_id = None, tmp_dir=None):
        # Directory of the current .py file
        self._module_path = Path(__file__).parent
        self._container_has_started = False
        self._session_id = session_id
        self._random_string = self._random_word()
        self._session_path = None
        self._seccomp_path = self._module_path / "settings/seccomp_profile.json"
        self._docker_nsjail_base_command = (
            "docker exec {session_id} nsjail "
            "--user 99999 --group 99999 "
            "--disable_proc --chroot / --really_quiet "
            "--time_limit {time_limit} "
        )

        # Generate a unique session ID
        while True:
            if tmp_dir is None:
                self._session_path = self._module_path / ".jailfs" / self._session_id
            else:
                self._session_path = Path(tmp_dir) / self._session_id

            if not os.path.exists(self._session_path):
                break

        # Create the .jailfs directory if needed
        if not (self._module_path / ".jailfs").is_dir():
            (self._module_path / ".jailfs").mkdir(parents=True, exist_ok=True)

        # Create the session path
        self._session_path.mkdir(parents=True, exist_ok=True)

        # Copy nsjail files into the session
        shutil.copytree(
            self._module_path / ".nsjail",
            self._session_path / ".nsjail"
        )

        # Let the child class provide the Dockerfile contents
        self._create_dockerfile()

        # Build the Docker image
        self._build_docker_image()

        # Run the Docker container in detached mode
        self._run_container()

    def __del__(self):
        # Cleanup when the object is destroyed
        if self._container_has_started:
            try:
                subprocess.run(
                    ["docker", "stop", self._session_id],
                    check=True,
                    stdout=subprocess.DEVNULL
                )
                subprocess.run(
                    f"docker image remove {self._session_id}_image --no-prune",
                    shell=True,
                    check=True,
                    stdout=subprocess.DEVNULL
                )
            except Exception:
                pass

        try:
            shutil.rmtree(self._session_path)
        except FileNotFoundError:
            pass

    # --------------------------------------------------------------------------
    # Child classes should override the following method with their Dockerfile
    # --------------------------------------------------------------------------
    def _create_dockerfile(self):
        """
        Return the contents of the Dockerfile as a string.
        This should be overridden by child classes.
        """
        raise NotImplementedError("Child class must implement _create_dockerfile().")

    # --------------------------------------------------------------------------
    # Internal helper methods
    # --------------------------------------------------------------------------
    def _build_docker_image(self):
        """
        Build the Docker image for this session.
        """
        build_cmd = f"docker build --network=host -t {self._session_id}_image ."
        result = subprocess.run(
            build_cmd,
            shell=True,
            cwd=self._session_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to build docker image: {result.stderr.decode('utf-8')}"
            )

    def _run_container(self):
        """
        Run the Docker container in detached mode.
        """
        run_cmd = (
            f'docker run --rm --privileged --security-opt seccomp={self._seccomp_path} --name={self._session_id} '
            f'-v "{self._session_path}:/volume" '
            f'-d -it {self._session_id}_image'
        )
        result = subprocess.run(
            run_cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Failed to start docker container: " + result.stderr.decode("utf-8")
            )
        self._container_has_started = True

    def _execute_file_in_volume(self, command_template, volume_filename, time_limit):
        """
        Execute a file inside the Docker container, using nsjail.
        :param command_template: Something like
            'docker exec {session_id} nsjail ... /usr/bin/python3 /volume/{volume_filename}'
        :param volume_filename: The filename we will pass into the command
        :param time_limit: The time limit in seconds
        :return: dict with keys "stdout", "stderr", "returncode"
        """
        command = command_template.format(
            session_id=self._session_id,
            time_limit=time_limit,
            volume_filename=volume_filename
        )
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
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

    # def _execute_code_in_memory(self, command_template, code_string, time_limit):
    #     """
    #     Execute code in memory (like 'python -c' or 'node -e') inside Docker + nsjail.
    #     :param command_template: Something like
    #         'docker exec {session_id} nsjail ... /usr/bin/python3 -c {code}'
    #     :param code_string: The user code
    #     :param time_limit: The time limit in seconds
    #     """
    #     quoted_code = shlex.quote(code_string)
    #     command = command_template.format(
    #         session_id=self._session_id,
    #         time_limit=time_limit,
    #         code=quoted_code
    #     )
    #     try:
    #         result = subprocess.run(
    #             command,
    #             shell=True,
    #             check=True,
    #             stdout=subprocess.PIPE,
    #             stderr=subprocess.PIPE
    #         )
    #         return {
    #             "stdout": result.stdout.decode("utf-8"),
    #             "stderr": result.stderr.decode("utf-8"),
    #             "returncode": result.returncode
    #         }
    #     except subprocess.CalledProcessError as e:
    #         return {
    #             "stdout": e.stdout.decode("utf-8"),
    #             "stderr": e.stderr.decode("utf-8"),
    #             "returncode": e.returncode
    #         }

    def _random_word(self):
        return str(uuid.uuid4())

# ------------------------------------------------------------------------------
# SafeEvalPython
# ------------------------------------------------------------------------------

class SafeEvalPython(SafeEval):
    """
    Child class for evaluating Python code.
    """

    def __init__(self, version=None, modules=None, tmp_dir=None):
        """
        :param version: Python version tag, e.g. 3.8
        :param modules: list of pip packages to install
        :param tmp_dir: optionally override the base directory for .jailfs
        """
        self._container_has_started = False
        self.python_version = version if version is not None else "3.8"
        self.modules = modules if modules else []
        self._session_id = "safe_eval_python" + self._random_word()
        super().__init__(tmp_dir=tmp_dir, session_id = self._session_id)

    def _create_dockerfile(self):
        # create Dockerfile
        with open(self._module_path / "Dockerfile_template_python.txt", "r") as f:
            Dockerfile = f.read()

        Dockerfile = Dockerfile.format(
            version=self.python_version, 
            modules="RUN pip3 install " + " ".join(self.modules)
        )

        with open(self._session_path / "Dockerfile", "w+") as f:
            f.write(Dockerfile)

    def eval(self, code=None, time_limit=SafeEval.max_timelimit, scope=None):
        """
        Evaluate Python code with optional time limit (seconds) and scope dict.
        """
        if code is None:
            return None

        if scope is None:
            scope = {}

        # Build Python lines that define each variable
        scope_definitions = "\n".join(
            f"{var} = {json.dumps(val)};"
            for var, val in scope.items()
        )

        # Wrap the code to capture the return value
        wrapped_code = (
            "import json\n"
            "try:\n"
            "    def user_code():\n"
            "        user_code = None\n"
            "        " + scope_definitions.replace("\n", "\n        ") + "\n"
            "        " + code.replace("\n", "\n        ") + "\n"  # Indent user code
            "    result = user_code()\n"
            "    print('" + self._random_string  + "' + json.dumps({'returnValue': result}))\n"
            "except Exception as e:\n"
            "    print(json.dumps({'error': str(e)}), file=sys.stderr)\n"
        )

        # Write to a temporary file in the volume
        volume_filename = self._random_word() + ".py"
        with open(self._session_path / volume_filename, "w", encoding="utf-8") as f:
            f.write(wrapped_code)

        # Command template for running the .py file
        python_command = (
            "docker exec {session_id} nsjail "
            "--user 99999 --group 99999 "
            "--disable_proc --chroot / --really_quiet "
            "--time_limit {time_limit} "
            "/usr/bin/python3 /volume/{volume_filename}"
        )
        return self._execute_file_in_volume(python_command, volume_filename, time_limit), self._random_string

# ------------------------------------------------------------------------------
# SafeEvalJavaScript
# ------------------------------------------------------------------------------

class SafeEvalJavaScript(SafeEval):
    """
    Child class for evaluating JavaScript code (Node.js).
    """

    def __init__(self, version=None, modules=None, tmp_dir=None):
        """
        :param version: Node.js version tag, e.g. '16',  etc.
        :param modules: list of npm packages to install globally
        :param tmp_dir: optionally override the base directory for .jailfs
        """
        self._container_has_started = False
        self.node_version = version if version is not None else "16"
        self.modules = modules if modules else []
        self._session_id = "safe_eval_javascript" + self._random_word()
        super().__init__(tmp_dir=tmp_dir, session_id = self._session_id)

    def _create_dockerfile(self):
        # create Dockerfile
        with open(self._module_path / "Dockerfile_template_javascript.txt", "r") as f:
            Dockerfile = f.read()

        Dockerfile = Dockerfile.format(
            version=self.node_version,
            modules="RUN npm install -g " + " ".join(self.modules) if self.modules else ""
        )

        with open(self._session_path / "Dockerfile", "w+") as f:
            f.write(Dockerfile)
            
    
    def eval(self, code=None, time_limit=SafeEval.max_timelimit, scope=None):
        """
        Evaluate JS code with optional time limit (seconds) and scope dict.
        """
        if code is None:
            return None

        if scope is None:
            scope = {}

        # Prepend scope variables as `let x = ...;`
        scope_definitions = "\n".join(
            f"let {var} = {json.dumps(val)};"
            for var, val in scope.items()
        )

        # Wrap the code to capture the return value
        wrapped_code = (
            scope_definitions +
            "\ntry {" +
            f"\n  const result = (() => {{ {code} }})();" +
            "\n  console.log('" +  self._random_string + "' + JSON.stringify({ returnValue: result }));" +
            "\n} catch (error) {" +
        "\n  console.error(JSON.stringify({ error: error.message }));" +
            "\n}"
        )

        # Write to a temporary file in the volume
        volume_filename = self._random_word() + ".js"
        with open(self._session_path / volume_filename, "w", encoding="utf-8") as f:
            f.write(wrapped_code)

        # Command template for running the .js file
        node_command = (
            self._docker_nsjail_base_command + 
            "/usr/bin/node /volume/{volume_filename}"
        )
        return self._execute_file_in_volume(node_command, volume_filename, time_limit), self._random_string


# ------------------------------------------------------------------------------
# Example usage
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Python example ===")
    py_eval = SafeEvalPython(version="3.8", modules=["requests"])
    result_py = py_eval.eval(
        code="""
import requests
print("Hello from Python!")
print("x:", x)
print("y:", y)
""",
        scope={"x": 100, "y": 200},
        time_limit=10
    )
    print("Python STDOUT:", result_py["stdout"])
    print("Python STDERR:", result_py["stderr"])
    print("Python RETURN CODE:", result_py["returncode"])

    print("=== JavaScript example ===")
    js_eval = SafeEvalJavaScript(version="16", modules=[])
    result_js = js_eval.eval(
        code="""
// Define x and y variables

// Example outputs
console.log("Hello from Node.js!");
console.log("x + 2 =", x + 2);
console.log("y * 3 =", y * 3);
""",
        scope={"x": 10, "y": 5},
        time_limit=10
    )
    print("JS STDOUT:", result_js["stdout"])
    print("JS STDERR:", result_js["stderr"])
    print("JS RETURN CODE:", result_js["returncode"])