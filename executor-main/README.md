making main() uncallable
making scope as variables rather than arguments so you can do shit like x:2 and y:x
update the weird hash mechanism of getting the return value
make it faster, its kinda slow
GPT processing of the output for simple user understanding.  LLM auto correct?
clear the docker process that created when running safe_eval
figure out networking
get the seccomp figured out
fix the damn imports in main.py
make everything neater
configure options for making containerization more modular depending on a bunch of flags
get it to work with additional types by specifying another field besides params like "dates" "bigints" and whatnot
how to stop using our shit to ddos
More robust tests
add Non-Root User to container and execute as him
Specify package versions
Run docker scan?
execute in memory rather than writing to file
remove dependencies once done
restrict programs to writing output to already-open file descriptors

# General Guidelines
Thank you for interviewing with Sample! This README should serve as the instructions for your interview, and if needed you can directly contact me at (408) 425 2215 or via email (aash@samplehc.com).

You should spend no more than 4-6 hours on this project! The goal is to get a working solution first, and then iterate on it. 

When you're done please invite @AashJ to a github repo.

# Python and JavaScript Evaluation

Sample Healthcare is the safest way to build and deploy safe AI applications that speed up operations by 10x without compromising on accuracy.

Most importantly, this offers our customers
- A glide path to AI agents
- Defaulting to the cutting edge
- Building an AI competency in house 


# Description

We build a flexible platform that allows customers to build and deploy AI agents for custom workflows. Our users write small code snippets with our custom building blocks and connect them together to create a workflow.

This project is building a small API that will take in a code snippet and evaluate it.

## API

We'll be deploying a separate service that has a single endpoint `/evaluate` that takes in a code snippet, a language, and evaluates it, and scope that is passsed into the evaluation. The project is scaffolded with FastAPI, but you can use whatever framework you want.

There's a couple of things to keep in mind:
- Evaluation must be safe – read on to see how I'd recommend doing this.
- Errors must be handled gracefully – errors in the evaluation should be throw upwards

Here are some helpful links to read through:

- [Figma – Server Side sandboxing: Containers and seccomp](https://www.figma.com/blog/server-side-sandboxing-containers-and-seccomp/#j1WRe)
- [HackerNews - Server Side sandboxing: Containers and seccomp](https://news.ycombinator.com/item?id=38000824)
- [PythonSafeEval](https://github.com/s3131212/PythonSafeEval)
- [WindMill - python_executor](https://github.com/windmill-labs/windmill/blob/main/backend/windmill-worker/src/python_executor.rs)

It seems like nsjail is the state of the art for fast execution of untrusted code. I'd recommend looking at WindMill and PythonSafeEval to get started. 

From my preliminary reading:
- PythonSafeEval launches a docker container and runs the code in it:
```python
    def __execute_file_in_volume(self, volume_filename, time_limit):
        command = "docker exec {session_id} nsjail --user 99999 --group 99999 --disable_proc --chroot / --really_quiet --time_limit {time_limit} /usr/bin/python3 /volume/{volume_filename}".format(session_id=self.__session_id, time_limit=time_limit, volume_filename=volume_filename)
```


## Installing NSJail

As mentioned above, we're using nsjail to sandbox our code. The first step should be to modify the Dockerfile to install nsjail.

From there, i'd recommend spinning up the container and ensuring that it is there!

## Evaluating Code

In our `/execute` endpoint we'll want to run a subprocess that will execute the code using nsjail. It should return the output of the executed code.


Here are some test cases to get started:


```
curl -X POST -H "Content-Type: application/json" -d '{"code": "return 1+1", "language": "python"}' http://localhost:8000/evaluate
```

The above should return `{"output": 2}`


```
curl -X POST -H "Content-Type: application/json" -d '{"code": "Invalid code!", "language": "python"}' http://localhost:8000/evaluate
```

The above should throw a ExecutionError with the message `SyntaxError: invalid syntax`

## Passing in scope

We should be able to pass in JSON scope to the `/evaluate` endpoint. For example, we could pass in a varaible called `x` with a value of 2.

Scope is passed in as a JSON object.

```
curl -X POST -H "Content-Type: application/json" -d '{"code": "return x", "language": "javascript", scope": {"x": 2}}' http://localhost:8000/evaluate
```

The above should return `{"output": 2}`

```
curl -X POST -H "Content-Type: application/json" -d '{"code": "return x + 3", "scope": {"x": 2}, "language": "javascript"}' http://localhost:8000/evaluate
```

The above should return `{"output": 5}`

## Additional features
- Handling different types, for example, how would we handle Dates or BigInts

## Development
1. Install [poetry](https://python-poetry.org/docs/)
2. Install dependencies with `poetry install`
3. You can run `poetry run python app/main.py` to run the server locally.

