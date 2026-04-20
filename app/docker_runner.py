import docker, tempfile, os, re
from uuid import uuid4

VALID_PATTERN = re.compile(
    r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?(==|>=|<=|>|<|!=)?\d*\.?\d*\.?\d*$'
)

def validate_requirements(requirements_text):
    for line in requirements_text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        package_part = line.split(";")[0].strip()
        if not VALID_PATTERN.match(package_part):
            return False, f"Invalid format: {line}. Expected: package_name or package_name==version"
    return True, "OK"

def run_student_code(code, input_data, timeout=10, image="python:3.11-slim", requirements=None):
    client = docker.from_env()

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "solution.py"), "w") as file:
            file.write(code)
        with open(os.path.join(tmpdir, "input.txt"), "w") as file:
            file.write(input_data)

        custom_image = None
        if requirements:
            custom_image = f"submission-{uuid4().hex[:8]}"
            build_dir = tempfile.mkdtemp()
            with open(os.path.join(build_dir, "Dockerfile"), "w") as f:
                f.write(f"FROM {image}\n")
                f.write("COPY requirements.txt /tmp/requirements.txt\n")
                f.write("RUN pip install -q -r /tmp/requirements.txt\n")
            with open(os.path.join(build_dir, "requirements.txt"), "w") as f:
                f.write(requirements)
            try:
                client.images.build(path=build_dir, tag=custom_image)
            except Exception as e:
                return {"status": "ERROR", "output": f"Failed to install requirements: {str(e)}"}
        try:
            result = client.containers.run(
                custom_image or image,
                command=f"sh -c 'timeout {timeout} python /code/solution.py < /code/input.txt'",
                volumes={tmpdir: {"bind": "/code", "mode": "ro"}},
                remove=True,
                mem_limit="128m",
                memswap_limit="128m",
                nano_cpus=500000000,
                network_disabled=True,
                read_only=True,
                pids_limit=10,
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
            )
            return {
                "status": "SUCCESS",
                "output": result.decode("utf-8").strip()
            }
        except docker.errors.ContainerError as e:
            if e.exit_status == 124:
                return {"status": "TIMEOUT", "output": "Time limit exceeded"}
            if e.exit_status == 137:
                return {"status": "ERROR", "output": "Memory limit exceeded"}
            return {"status": "ERROR", "output": str(e)}
        except docker.errors.ImageNotFound:
            return {"status": "ERROR", "output": "Docker image not found"}
        except docker.errors.APIError as e:
            return {"status": "ERROR", "output": f"Docker error: {str(e)}"}
        except Exception as e:
            return {"status": "ERROR", "output": f"System error: {str(e)}"}
        finally:
            if custom_image:
                try:
                    client.images.remove(custom_image, force=True)
                except:
                    pass