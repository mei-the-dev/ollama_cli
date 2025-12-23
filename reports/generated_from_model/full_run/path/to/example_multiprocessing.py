#!/usr/bin/env python3

import multiprocessing
import time

def cpu_bound_task(n):
    # A simple CPU-bound task that calculates the sum of squares up to n
    return sum(i * i for i in range(n))

def main():
    # Number of processes to use, typically set to the number of CPU cores available
    num_processes = multiprocessing.cpu_count()
    print(f'Number of CPU cores: {num_processes}')
    
    # List of numbers to process
    numbers = [10**6, 2*10**6, 3*10**6, 4*10**6, 5*10**6]
    
    # Create a multiprocessing pool with the specified number of processes
    with multiprocessing.Pool(processes=num_processes) as pool:
        # Map the CPU-bound task to each number in the list and collect results
        results = pool.map(cpu_bound_task, numbers)
        
    # Print the results
    for number, result in zip(numbers, results):
        print(f'Sum of squares up to {number}: {result}')

if __name__ == '__main__':
    main()
