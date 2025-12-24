#!/usr/bin/env python3

import json
import sys
import time

import psutil


def collect_metrics(command):
    # Start the process and record the start time
    process = psutil.Popen(command, shell=True)
    start_time = time.time()

    # Initialize metrics dictionary
    metrics = {"memory_usage": [], "cpu_usage": [], "runtime": 0}

    try:
        while True:
            # Check if the process is still running
            if process.poll() is None:
                # Get memory and CPU usage
                mem_info = process.memory_info()
                cpu_percent = process.cpu_percent(interval=1)

                # Append metrics to lists
                metrics["memory_usage"].append(mem_info.rss)  # Resident Set Size in bytes
                metrics["cpu_usage"].append(cpu_percent)
            else:
                break
    except KeyboardInterrupt:
        print("Metrics collection interrupted by user.")
    finally:
        # Calculate total runtime
        metrics["runtime"] = time.time() - start_time

        # Wait for the process to complete and get return code
        return_code = process.wait()
        metrics["return_code"] = return_code

    return metrics


def write_metrics_to_json(metrics, output_file):
    with open(output_file, "w") as f:
        json.dump(metrics, f, indent=4)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python telemetry_collector.py <command> <output_file>")
        sys.exit(1)

    command = sys.argv[1]
    output_file = sys.argv[2]

    # Collect metrics for the given command
    collected_metrics = collect_metrics(command)

    # Write metrics to a JSON file
    write_metrics_to_json(collected_metrics, output_file)
    print(f"Metrics written to {output_file}")
