import docker, tempfile, os, re, time
from uuid import uuid4

client = docker.from_env()

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

def build_custom_image(image, requirements):
    custom_image = f"submission-{uuid4().hex[:8]}"
    build_dir = tempfile.mkdtemp()
    with open(os.path.join(build_dir, "Dockerfile"), "w") as f:
        f.write(f"FROM {image}\n")
        f.write("COPY requirements.txt /tmp/requirements.txt\n")
        f.write("RUN pip install -q -r /tmp/requirements.txt\n")
    with open(os.path.join(build_dir, "requirements.txt"), "w") as f:
        f.write(requirements)
    build_start = time.time()
    client.images.build(path=build_dir, tag=custom_image)
    build_time = round(time.time() - build_start, 3)
    return custom_image, build_time

def run_student_code(code, input_data, timeout=10, image="python:3.11-slim", requirements=None):
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "solution.py"), "w") as file:
            file.write(code)
        with open(os.path.join(tmpdir, "input.txt"), "w") as file:
            file.write(input_data)

        try:
            run_start = time.time()
            result = client.containers.run(
                image,
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
            run_time = round(time.time() - run_start, 3)

            return {
                "status": "SUCCESS",
                "output": result.decode("utf-8").strip(),
                "run_time": run_time,
            }
        except docker.errors.ContainerError as e:
            run_time = round(time.time() - run_start, 3)
            if e.exit_status == 124:
                return {"status": "TIMEOUT", "output": "Time limit exceeded", "run_time": run_time}
            if e.exit_status == 137:
                return {"status": "ERROR", "output": "Memory limit exceeded", "run_time": run_time}
            return {"status": "ERROR", "output": str(e), "run_time": run_time}
        except docker.errors.ImageNotFound:
            return {"status": "ERROR", "output": "Docker image not found", "run_time": 0}
        except docker.errors.APIError as e:
            return {"status": "ERROR", "output": f"Docker error: {str(e)}", "run_time": 0}
        except Exception as e:
            return {"status": "ERROR", "output": f"System error: {str(e)}", "run_time": 0}
        
def run_all_tests(code, tests_data, timeout=10, image="python:3.11-slim", requirements=None):
    custom_image = None
    build_time = None

    if requirements:
        try:
            custom_image, build_time = build_custom_image(image, requirements)
        except Exception as e:
            return None, None, f"Failed to install requirements: {str(e)}"

    run_image = custom_image or image

    results = []
    all_passed = True
    total_run_time = 0

    for test in tests_data:
        result = run_student_code(code, test["input"], image=run_image, timeout=timeout)
        passed = (result["status"] == "SUCCESS"
                 and result["output"] == test["expected"].strip())
        total_run_time += result["run_time"]
        results.append({
            "input": test["input"],
            "expected": test["expected"],
            "actual": result["output"],
            "status": result["status"],
            "passed": passed,
            "run_time": result["run_time"]
        })
        if not passed:
            all_passed = False

    if custom_image:
        try:
            client.images.remove(custom_image, force=True)
        except:
            pass

    return results, {"all_passed": all_passed, "build_time": build_time, "total_run_time": round(total_run_time, 3)
    }, None