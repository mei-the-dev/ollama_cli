# Import necessary libraries
import multiprocessing
import time


def cpu_bound_task(n):
    # Simulate a CPU-bound task by summing numbers up to n
    return sum(i * i for i in range(n))


def main():
    # Number of processes to use
    num_processes = multiprocessing.cpu_count()
    print(f"Using {num_processes} processes")

    # List of tasks to be processed
    tasks = [10**6, 2 * 10**6, 3 * 10**6, 4 * 10**6, 5 * 10**6]

    # Create a pool of processes
    with multiprocessing.Pool(processes=num_processes) as pool:
        # Map the tasks to the pool and get results
        results = pool.map(cpu_bound_task, tasks)

    # Print the results
    for task, result in zip(tasks, results):
        print(f"Task with n={task} completed. Result: {result}")


if __name__ == "__main__":
    main()
