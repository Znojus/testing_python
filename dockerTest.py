import docker

client = docker.from_env()

result = client.containers.run(
    "python:3.11-slim",
    command="sh -c 'python /code/solution.py < /code/input.txt'",
    volumes={"C:\\Users\\znoju\\Desktop\\docker-test": {"bind": "/code", "mode": "ro"}},
    remove=True,
    mem_limit="128m",
    memswap_limit="128m",
    network_disabled=True,
    read_only=True,
    pids_limit=10,
    cap_drop=["ALL"],
    security_opt=["no-new-privileges:true"],
)

print(result.decode("utf-8"))
