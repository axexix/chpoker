CONTAINER_NAME = chpoker


image :
	podman build -t $(CONTAINER_NAME):latest .

run:
	podman run --rm -ti --name $(CONTAINER_NAME) --userns=keep-id -v "${PWD}:/home/dev/src" -v cache:/home/dev/.cache -p 8080:8080 -p 9000:9000 chpoker:latest poetry run pylsp --tcp --host 0.0.0.0 --port 9000

stop:
	podman stop "$(CONTAINER_NAME)"

shell :
	podman exec -ti $(CONTAINER_NAME) poetry shell

clean :
	podman rm -f $(CONTAINER_NAME)
