#!/usr/bin/env python3
import json
import time

import psutil


def collect_metrics(command):
    # Start the process and record start time
    process = psutil.Popen(command, shell=True)
    start_time = time.time()

    # Initialize metrics dictionary
    metrics = {
        "command": command,
        "start_time": start_time,
        "end_time": None,
        "runtime": None,
        "memory_usage": [],
        "cpu_usage": [],
    }

    try:
        while process.poll() is None:
            # Record memory and CPU usage every second
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent(interval=1)

            metrics["memory_usage"].append(
                {
                    "timestamp": time.time(),
                    "rss": memory_info.rss,  # Resident Set Size
                    "vms": memory_info.vms,  # Virtual Memory Size
                }
            )

            metrics["cpu_usage"].append({"timestamp": time.time(), "percent": cpu_percent})
    except Exception as e:
        print(f"Error collecting metrics: {e}")

    # Record end time and runtime
    metrics["end_time"] = time.time()
    metrics["runtime"] = metrics["end_time"] - start_time

    return metrics


def write_metrics_to_json(metrics, output_file):
    with open(output_file, "w") as f:
        json.dump(metrics, f, indent=4)


if __name__ == "__main__":
    command = "your_command_here"  # Replace with the actual command to run
    metrics = collect_metrics(command)
    output_file = "/path/to/output.json"
    write_metrics_to_json(metrics, output_file)
