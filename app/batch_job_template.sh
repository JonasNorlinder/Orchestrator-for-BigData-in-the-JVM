#!/bin/zsh

# baseline
repeat 5 { ./benchmark.py --tag=baseline --duration=1 --threads=6 --skew=-6 \
          --jdkClient=~/.sdkman/candidates/java/20.ea.4-open \
          --jvmClientArgs="-XX:+UseG1GC -Xms32G -Xmx32G" \
          --jdkServer=~/jdk/custom/build/linux-x86_64-server-release/jdk \
          --jvmServerArgs="-XX:+UseZGC -XX:+UnlockDiagnosticVMOptions -XX:-ZBufferStoreBarriers -Xms64G -Xmx64G" \
          --perf="cache-misses,branch"
}

# target
repeat 5 { ./benchmark.py --tag=patch --duration=1 --threads=6 --skew=-6 \
          --jdkClient=~/.sdkman/candidates/java/20.ea.4-open \
          --jvmClientArgs="-XX:+UseG1GC -Xms32G -Xmx32G" \
          --jdkServer=~/jdk/custom/build/linux-x86_64-server-release/jdk \
          --jvmServerArgs="-XX:+UseZGC -XX:+UnlockDiagnosticVMOptions -XX:-ZBufferStoreBarriers -Xms64G -Xmx64G" \
          --perf="cache-misses,branch"
}