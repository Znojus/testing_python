import docker, tempfile, os

def run_student_code(code, input_data, timeout=10):
    client = docker.from_env()

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "solution.py"), "w") as file:
            file.write(code)
        with open(os.path.join(tmpdir, "input.txt"), "w") as file:
            file.write(input_data)

        try:
            result = client.containers.run(
                "python:3.11-slim",
                command=f"sh -c 'timeout {timeout} python /code/solution.py < /code/input.txt'",
                volumes={tmpdir: {"bind": "/code", "mode": "ro"}},
                remove=True,
                mem_limit="128m",
                memswap_limit="128m",
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