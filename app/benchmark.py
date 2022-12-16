#!/usr/bin/python3

import pathlib
import signal
import subprocess
import os
import sys
import time
import traceback
from enum import Enum
import argparse
from typing import Dict, Final
from multiprocessing import Process
from shared.utils import ask_y_n, has_key

class CassandraVars:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CassandraVars, cls).__new__(cls)
        return cls._instance

    base_dir: Final[str] = os.path.dirname(os.path.realpath(__file__))
    cassandra_bin: Final[str] = base_dir + "/bin/cassandra"
    nodetool_bin: Final[str] = base_dir + "/bin/nodetool"
    cassanadra_stress_bin: Final[str] = base_dir + \
        "/tools/bin/cassandra-stress"
    perf: str = ""
    perf_file: Final[str] = base_dir + "/bin/PERF"
    java_dir: Dict = {"client": "", "server": ""}
    user_jvm_args: str = ""
    user_jvm_server_args: str = ""
    user_jvm_client_args: str = ""
    old_java_home: str = ""
    duration: str = ""
    threads: str = ""
    old_jvm_opts: str = ""
    tag: str = ""
    skew: int = 0
    cpu_count: int = 0
    kill_java_on_exit: bool = True
    debug: bool = False


CassandraVars()


class ServerStatus(Enum):
    READY = 0
    DEAD = 1
    BOOTING = 2


def write_configuration(result_path: str) -> None:
    with open(os.path.join(result_path, "configuration"), "w") as writeFile:
        writeFile.write("== Build info ==\n")
        writeFile.write("Path to server jdk: " +
                        CassandraVars.java_dir["server"] + "\n")
        writeFile.write("Path to client jdk: " +
                        CassandraVars.java_dir["client"] + "\n")
        writeFile.write("User supplied JVM arguments for both client/server: " +
                        CassandraVars.user_jvm_args + "\n")
        writeFile.write("User supplied JVM arguments for server: " +
                        CassandraVars.user_jvm_server_args + "\n")
        writeFile.write("User supplied JVM arguments for client: " +
                        CassandraVars.user_jvm_client_args + "\n\n")
        writeFile.write("\n== Build release info ==\n")
        writeFile.write("Server build release file:\n")
        if os.path.exists(os.path.join(CassandraVars.java_dir["server"], "release")):
            with open(os.path.join(CassandraVars.java_dir["server"], "release"), "r") as f:
                for l in f:
                    writeFile.write(l)
        else:
            writeFile.write("Could not find server release file")
        writeFile.write("\nClient build release file:\n")
        if os.path.exists(os.path.join(CassandraVars.java_dir["client"], "release")):
            with open(os.path.join(CassandraVars.java_dir["client"], "release"), "r") as f:
                for l in f:
                    writeFile.write(l)
        else:
            writeFile.write("Could not find client release file")
        writeFile.write("\n== Cassandra info ==\n")
        writeFile.write("Client threads: " + CassandraVars.threads + "\n")
        writeFile.write("Duration: " + CassandraVars.duration + "\n")
        writeFile.write("Workload: cqlstress-insanity-example.yaml" + "\n")


def write_in_new_process(result_path, app) -> None:
    with open(os.path.join(result_path, "server.log"), "w") as writeFile:
        for l in app.stdout:  # type: ignore
            writeFile.write(l)


def run_cassandra_server(result_path: str) -> None:
    os.environ["JAVA_HOME"] = CassandraVars.java_dir["server"]
    init_user_jvm_args()
    add_jvm_option(CassandraVars.user_jvm_server_args)
    add_jvm_option("".join(["-Xlog:gc*:file=", result_path, "/server.gc"]))
    x = " ".join(["taskset -c", get_server_cpu_affinity_group(),
                  CassandraVars.cassandra_bin])
    app = subprocess.Popen(x, shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)

    if len(CassandraVars.perf) > 0:
        p = Process(target=write_in_new_process, args=[result_path, app])
        p.start()
        time.sleep(15)
    else:
        write_in_new_process(result_path, app)
    restore_jvm_opts()


def run_cassandra_stress(duration: str, threads: str, result_path: str) -> None:
    os.environ["JAVA_HOME"] = CassandraVars.java_dir["client"]
    print("Running workload")
    init_user_jvm_args()
    add_jvm_option(CassandraVars.user_jvm_client_args)
    add_jvm_option("".join(["-Xlog:gc*:file=", result_path, "/client.gc"]))
    conf = "user profile="+CassandraVars.base_dir + \
        "/tools/cqlstress-insanity-example.yaml ops\(insert=3,simple1=7\) duration=" + duration + \
        " no-warmup cl=ONE -pop dist=UNIFORM\(1..100000000\) -mode native cql3 -rate threads=" + threads
    x = " ".join(["taskset -c " + get_client_cpu_affinity_group(),
                  CassandraVars.cassanadra_stress_bin, conf])
    app = subprocess.Popen(x, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, shell=True, universal_newlines=True)

    with open(os.path.join(result_path, "client.log"), "w") as writeFile:
        for l in app.stdout:  # type: ignore
            writeFile.write(l)

    block_until_process_is_done(app)
    restore_jvm_opts()
    request_graceful_server_exit()


def block_until_process_is_done(app) -> int:
    app.communicate()
    return app.returncode


def get_server_cpu_affinity_group() -> str:
    lo: str = str(0)
    hi: str = str(int(CassandraVars.cpu_count/2) - 1 - CassandraVars.skew)
    return "-".join([lo, hi])


def get_client_cpu_affinity_group() -> str:
    lo: str = str(int(CassandraVars.cpu_count/2) - CassandraVars.skew)
    hi: str = str(CassandraVars.cpu_count)
    return "-".join([lo, hi])


def validate_XmxXms_pair(jvmArgs: str) -> None:
    if "Xmx" in jvmArgs and not "Xms" in jvmArgs or "Xms" in jvmArgs and not "Xmx" in jvmArgs:
        print("Must specify Xmx and Xms in pairs")
        raise Exception()


def validate_perf() -> None:
    if len(CassandraVars.perf) == 0:
        raise Exception()
    x = " ".join(["perf stat -e", CassandraVars.perf, "echo"])
    app = subprocess.Popen(x, shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
    current = ""
    for l in app.stdout:  # type: ignore
        current += l
    if block_until_process_is_done(app) != 0:
        print("Validation failed: supplied perf event list seems to be broken", flush=True)
        print(current)
        exit(1)


def validate_jvm_args_run(x: str, key: str) -> None:
    app = subprocess.Popen(x, shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
    current = ""
    for l in app.stdout:  # type: ignore
        current += l
    if block_until_process_is_done(app) != 0:
        print("Validation failed: supplied JVM arguments seems to be broken (" + key + ")", flush=True)
        print(current)
        exit(1)


def validate_jvm_args() -> None:
    for (key, val) in CassandraVars.java_dir.items():
        if key == "client":
            x = " ".join([val + "/bin/java", CassandraVars.user_jvm_args,
                          CassandraVars.user_jvm_client_args, "-version"])
        else:
            x = " ".join([val + "/bin/java", CassandraVars.user_jvm_args,
                          CassandraVars.user_jvm_server_args, "-version"])
        validate_jvm_args_run(x, key)


def clear_perf() -> None:
    x = " ".join(["rm -f", CassandraVars.perf_file])
    delete = subprocess.Popen(x, shell=True)
    block_until_process_is_done(delete)


def get_path(name: str) -> str:
    base_dir_results: str = os.path.join(
        CassandraVars.base_dir, name, CassandraVars.tag)
    pathlib.Path(base_dir_results).mkdir(parents=True, exist_ok=True)
    count_previous_result = len(next(os.walk(base_dir_results))[1])
    result_path = os.path.join(base_dir_results, str(count_previous_result))
    pathlib.Path(result_path).mkdir(parents=True, exist_ok=True)
    return result_path


def get_result_path() -> str:
    return get_path("results")


def get_init_path() -> str:
    return get_path("init_data_logs")


def init_user_jvm_args() -> None:
    if len(CassandraVars.user_jvm_args) > 0:
        add_jvm_option(CassandraVars.user_jvm_args)


def add_jvm_option(option: str) -> None:
    if has_key(os.environ, "JVM_OPTS"):
        os.environ["JVM_OPTS"] = " ".join([os.environ["JVM_OPTS"], option])
    else:
        os.environ["JVM_OPTS"] = option


def init_old_jvm_opts() -> None:
    if has_key(os.environ, "JVM_OPTS"):
        CassandraVars.old_jvm_opts = os.environ["JVM_OPTS"]


def restore_jvm_opts() -> None:
    if len(CassandraVars.old_jvm_opts) > 0:
        os.environ["JVM_OPTS"] = CassandraVars.old_jvm_opts
    else:
        if has_key(os.environ, "JVM_OPTS"):
            del os.environ["JVM_OPTS"]


def prepopulate_tasks() -> None:
    path = get_init_path()
    run_cassandra_server(path)
    block_until_ready()

    # 100000000
    prepopulate_database(int(100000000 / 8), path)

    request_graceful_server_exit()
    block_until_dead()

    copy = subprocess.Popen(" ".join(["cp -r", os.path.join(CassandraVars.base_dir, "data"), os.path.join(
        CassandraVars.base_dir, "pre_data")]), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    block_until_process_is_done(copy)
    restore_jvm_opts()


def prepare_yes():
    prepopulate_tasks()
    print("Done prepopulating the database. Please try starting command again")
    exit(0)


def prepare_database() -> None:
    x = " ".join(["rm -rf", os.path.join(CassandraVars.base_dir, "data")])
    delete = subprocess.Popen(x, shell=True)
    block_until_process_is_done(delete)

    if os.path.exists(os.path.join(CassandraVars.base_dir, "pre_data")):
        copy = subprocess.Popen(" ".join(["cp -r", os.path.join(CassandraVars.base_dir, "pre_data"), os.path.join(
            CassandraVars.base_dir, "data")]), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        block_until_process_is_done(copy)
        return

    ask_y_n("It seems that you don't have a prepopulated database which is needed for stable benchmark results. Do you want to generate it now? It takes about 20 minutes and will uses about 4 GB of hard drive space.", prepare_yes, exit_on_no)


def prepopulate_database(N: int, path: str) -> None:
    init_user_jvm_args()

    conf = "user profile="+CassandraVars.base_dir+"/tools/cqlstress-insanity-example.yaml ops\(insert=1\) no-warmup cl=ONE n=" + str(
        int(N))+" -mode native cql3 -pop seq=1.."+str(N)+" -rate threads=" + CassandraVars.threads
    add_jvm_option("".join(["-Xlog:gc*:file=", path, "/client.gc"]))
    x = " ".join(["taskset -c " + get_client_cpu_affinity_group(),
                  CassandraVars.cassanadra_stress_bin, conf])
    app = subprocess.Popen(x, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
    with open(os.path.join(path, "client.log"), "w") as writeFile:
        for l in app.stdout:  # type: ignore
            writeFile.write(l)

    block_until_process_is_done(app)
    restore_jvm_opts()


def nodetool_status() -> ServerStatus:
    app = subprocess.Popen([CassandraVars.nodetool_bin, "status"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    block_until_process_is_done(app)
    status_code = app.returncode
    if status_code == 0:
        return ServerStatus.READY
    elif status_code == 1:
        return ServerStatus.DEAD
    elif status_code == 2:
        return ServerStatus.BOOTING
    else:
        raise Exception("Unkown nodetool status code")


def request_graceful_server_exit() -> None:
    app = subprocess.Popen([CassandraVars.nodetool_bin, "stopdaemon"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    block_until_process_is_done(app)


def block_until(status) -> None:
    while True:
        time.sleep(5)
        nodetool_code = nodetool_status()
        if nodetool_code == status:
            print(" done", flush=True)
            return
        elif nodetool_code == ServerStatus.DEAD:
            print(
                "\nCassandra crashed, checks the logs for more info. Aborting...", flush=True)
            exit(1)
        print(".", end="", flush=True)


def block_until_ready() -> None:
    print("Blocking until server is ready: ", end="", flush=True)
    block_until(ServerStatus.READY)


def block_until_dead() -> None:
    print("Blocking until server is dead: ", end="", flush=True)
    block_until(ServerStatus.DEAD)


def init() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--jdk", help="path to JDK, use same for client and server")
    parser.add_argument(
        "--jdkServer", help="path to JDK to be used for server")
    parser.add_argument(
        "--jdkClient", help="path to JDK to be used for client")
    parser.add_argument("--tag", help="tag name", required=True)
    parser.add_argument(
        "--duration", help="duration in minutes (default 1)", default=1)
    parser.add_argument(
        "--threads", help="client threads (default 1)", default=1)
    parser.add_argument(
        "--skew", help="skew CPU partitioning (default 0)", default=0)
    parser.add_argument(
        "--perf", help="arguments to perf stat -e (default None)")
    parser.add_argument(
        "--jvmArgs", help="args to both client and server JVM (e.g. \"-XX:+UseZGC -XX:+ShowMessageBoxOnError\")")
    parser.add_argument("--jvmClientArgs",
                        help="args to client JVM (e.g. \"-XX:+UseG1GC\")")
    parser.add_argument("--jvmServerArgs",
                        help="args to server JVM (e.g. \"-XX:+UseZGC\")")
    parser.add_argument("--autoKillJava", help="automatically kill any previously running Java processess before starting server", action='store_true')
    parser.add_argument("--debug", help="debug this tool", action='store_true')
    args = parser.parse_args()

    if args.autoKillJava:
        check_if_java_is_running_non_interactive()
    else:
        check_if_java_is_running_interactive()

    if args.jdk is None and args.jdkServer is None and args.jdkClient is None:
        print("Must specify either jdk or jdkServer/jdkClient")
        raise Exception()

    if args.jdk is not None:
        if args.jdkServer is not None or args.jdkClient is not None:
            print(
                "Can't set both jdk and jdkServer/jdkClient, use jdk only or jdkServer/jdkClient in pair")
            raise Exception()
        CassandraVars.java_dir["client"] = os.path.expanduser(args.jdk)
        CassandraVars.java_dir["server"] = os.path.expanduser(args.jdk)
    elif args.jdkServer is not None or args.jdkClient is not None:
        if args.jdkServer is None or args.jdkClient is None:
            print("Must specify jdkClient and jdkServer in pair")
            exit(1)
        CassandraVars.java_dir["client"] = os.path.expanduser(args.jdkClient)
        CassandraVars.java_dir["server"] = os.path.expanduser(args.jdkServer)

    if len(CassandraVars.java_dir["client"]) == 0 or len(CassandraVars.java_dir["server"]) == 0:
        raise Exception()

    cpu_count = os.cpu_count()
    if cpu_count is None or cpu_count == 0:
        raise Exception()
    CassandraVars.cpu_count = int(cpu_count)

    if args.jvmArgs is not None:
        validate_XmxXms_pair(args.jvmArgs)
        CassandraVars.user_jvm_args = args.jvmArgs

    if args.jvmClientArgs is not None:
        validate_XmxXms_pair(args.jvmClientArgs)
        CassandraVars.user_jvm_client_args = args.jvmClientArgs

    if args.jvmServerArgs is not None:
        validate_XmxXms_pair(args.jvmServerArgs)
        CassandraVars.user_jvm_server_args = args.jvmServerArgs

    CassandraVars.tag = args.tag
    if args.debug:
        CassandraVars.debug = True
    else:
        sys.tracebacklimit = 0
        signal.signal(signal.SIGINT, lambda x, y: sys.exit(signal.SIGINT))

    CassandraVars.skew = int(args.skew)
    if abs(CassandraVars.skew) > CassandraVars.cpu_count/2 - 1:
        print("Invalid skew value. Must have room for both server and client")
        raise Exception()
    print("Using CPUs [" + get_server_cpu_affinity_group() + "] for server")
    print("Using CPUs [" + get_client_cpu_affinity_group() + "] for client")

    for x in [CassandraVars.cassandra_bin, CassandraVars.cassanadra_stress_bin, CassandraVars.nodetool_bin, CassandraVars.java_dir["client"] + "/bin/java", CassandraVars.java_dir["server"] + "/bin/java"]:
        if not os.path.isfile(x):
            print("Could not find '" + x + "' binary. Check your configuration")
            raise Exception()

    CassandraVars.duration = str(args.duration) + "m"
    CassandraVars.threads = str(int(args.threads))
    validate_jvm_args()

    clear_perf()
    if args.perf is not None:
        CassandraVars.perf = args.perf
        validate_perf()
        with open(CassandraVars.perf_file, "w") as writeFile:
            writeFile.write(args.perf)


def exit_on_no():
    print("OK. Exiting...")
    CassandraVars.kill_java_on_exit = False
    exit(1)


def check_if_java_is_running_yes():
    app = subprocess.Popen(["pkill java"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, shell=True)
    print("Killing all Java processes...")
    block_until_process_is_done(app)
    time.sleep(5)
    check_if_java_is_running_non_interactive()


def check_if_java_is_running():
    app = subprocess.Popen(["pgrep java"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, shell=True)
    return block_until_process_is_done(app)


def check_if_java_is_running_interactive():
    if check_if_java_is_running() != 1:
        ask_y_n("Java processes are already running. Do you want to kill them?",
                check_if_java_is_running_yes, exit_on_no)

def check_if_java_is_running_non_interactive():
    while check_if_java_is_running() != 1:
        app = subprocess.Popen(["pkill java"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, shell=True)
        block_until_process_is_done(app)
        time.sleep(5)

def main() -> None:
    if has_key(os.environ, "JAVA_HOME"):
        CassandraVars.old_java_home = os.environ["JAVA_HOME"]
    try:
        init()
        prepare_database()
        result_path = get_result_path()

        write_configuration(result_path)

        run_cassandra_server(result_path)
        block_until_ready()

        run_cassandra_stress(CassandraVars.duration,
                             CassandraVars.threads, result_path)
        block_until_dead()
        print("Results stored in: " + result_path)
    except Exception:
        if CassandraVars.debug:
            print(traceback.format_exc())
        exit(1)
    finally:
        if len(CassandraVars.old_java_home) > 0:
            os.environ["JAVA_HOME"] = CassandraVars.old_java_home
        restore_jvm_opts()
        if CassandraVars.kill_java_on_exit:
            print("\nWorkload has finished, killing any remaining Java processes")
            # forcefully kill since we might have failed doing a graceful exit
            subprocess.Popen(["pkill java"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, shell=True)


if __name__ == "__main__":
    main()
