#!/usr/bin/env python3

import subprocess
from resource import setrlimit, RLIMIT_AS, RLIMIT_CPU
import signal
def limit_subprocess_resources(command, timeout=10, memory_limit_mb=512):
    # Convert memory limit from MB to bytes
    memory_limit_bytes = memory_limit_mb * 1024 * 1024
    
    # Set CPU time limit
    setrlimit(RLIMIT_CPU, (timeout, timeout))
    
    # Set memory usage limit
    setrlimit(RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
    
    try:
        # Start the subprocess with limited resources
        process = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process.stdout.decode(), process.stderr.decode()
    except subprocess.CalledProcessError as e:
        return e.stdout.decode(), e.stderr.decode()
    except Exception as e:
        return '', str(e)

if __name__ == '__main__':
    # Example usage: limit the execution of 'ls -l' to 10 seconds and 512 MB memory
    stdout, stderr = limit_subprocess_resources(['ls', '-l'])
    print('stdout:', stdout)
    print('stderr:', stderr)