# Orchestrator for BigData in JVM

## What is this? Why?

These scripts are created to run Cassandra 4.1.0 benchmarks on a single local machine to gauge performance behavior while developing GC related stuff for OpenJDK.

## Installation

Download the [latest](https://github.com/JonasNorlinder/Orchestrator-for-BigData-in-JVM/releases/download/latest/Orchestrator-for-BigData-in-JVM.tar.gz) build of this tool. You need Python 3 and a modern version of Linux in order to run this tool. Scripts are included to download and install Cassandra 4.1.0 into the folder `app`. To do this execute `./install_cassandra.sh`. If you prefer manually downloading Cassandra make sure that you copy the patch files in `patch_files` into `app`.

## Running Cassandra

Before running the benchmark script you must change the current working directory to `app` (i.e. run the command `cd app`). The script takes the following arguments:

```
usage: benchmark.py [-h] [--jdk JDK] [--jdkServer JDKSERVER] [--jdkClient JDKCLIENT] --tag TAG
                    [--duration DURATION] [--threads THREADS] [--skew SKEW] [--perf PERF] [--jvmArgs JVMARGS]
                    [--jvmClientArgs JVMCLIENTARGS] [--jvmServerArgs JVMSERVERARGS] [--debug DEBUG]

optional arguments:
  -h, --help            show this help message and exit
  --jdk JDK             path to JDK, use same for client and server
  --jdkServer JDKSERVER
                        path to JDK to be used for server
  --jdkClient JDKCLIENT
                        path to JDK to be used for client
  --tag TAG             tag name
  --duration DURATION   duration in minutes (default 1)
  --threads THREADS     client threads (default 1)
  --skew SKEW           skew CPU partitioning (default 0)
  --perf PERF           arguments to perf stat -e (default None)
  --jvmArgs JVMARGS     args to both client and server JVM (e.g. "-XX:+UseZGC -XX:+ShowMessageBoxOnError")
  --jvmClientArgs JVMCLIENTARGS
                        args to client JVM (e.g. "-XX:+UseG1GC")
  --jvmServerArgs JVMSERVERARGS
                        args to server JVM (e.g. "-XX:+UseZGC")
  --debug DEBUG         debug this tool
```

As an example you could start a benchmark for 2 minutes using up to 10 Cassandra threads like this:
```
./benchmark.py --jdk=~/my_custom_build/linux-x86_64-server-release/jdk --tag=test --duration=2 --threads=10 --jvmArgs="-XX:+UseZGC -Xmx32G -Xmx32G" --perf="cache-misses,branches"
```

Please not that Cassandra forces you to specify `-Xms -Xmx` in pairs. Also note that Cassandra needs the JDK to be at least version 14 or above. You will find the output of runs in `app/results/${TAG}/{NUM}`. If no arguments is given to `--perf` then Cassandra server will be started normally, i.e. no perf at all. Output of perf would be found when server has exited in `server.log`.

## Generating a statistical report

Python requirements: pandas (install using `pip3 install pandas`)

Using `app/generate_report.py` you can generate a summarized report on all metrics for each tag. Must have `app` as working directory. In the root folder of each tag you will find the report in HTML format, e.g. for tag `zgc_generational` you would find your HTML report in `app/results/zgc_generational/summary.html`.

## Configuration

Both client and server currently uses the same `jvmArgs` and both are defaulting to log with `-Xlog:gc*`. This could easily be changed in `benchmark.py`.

## Development notes

Stack trace is enabled using `--debug=true`.

### Suggestions

Feel free to submit an issue or make a pull request if you think something could be done better.

