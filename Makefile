CONTAINER_NAME = chpoker


image :
	podman build -t $(CONTAINER_NAME):latest .

shell :
	podman run --rm -ti --name $(CONTAINER_NAME) -v "${PWD}:/src" -v cache:/root/.cache -p 8080:8080 chpoker:latest poetry shell

clean :
	podman rm -f $(CONTAINER_NAME)
