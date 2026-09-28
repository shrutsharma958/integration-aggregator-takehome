import concurrent.futures
import statistics
import sys
import time
import urllib.request


URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080/healthz"

CONCURRENCY_LEVELS = [1, 5, 10]
REQUESTS_PER_LEVEL = 100


def request():
    start = time.perf_counter()

    with urllib.request.urlopen(URL, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected status: {response.status}")
        response.read()

    return (time.perf_counter() - start) * 1000


def percentile(values, percentile):
    values = sorted(values)
    index = int((percentile / 100) * (len(values) - 1))
    return values[index]


def benchmark(concurrency):
    start = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=concurrency
    ) as executor:
        latencies = list(
            executor.map(
                lambda _: request(),
                range(REQUESTS_PER_LEVEL),
            )
        )

    elapsed = time.perf_counter() - start

    return {
        "concurrency": concurrency,
        "requests": REQUESTS_PER_LEVEL,
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "throughput_rps": REQUESTS_PER_LEVEL / elapsed,
        "errors": 0,
    }


def main():
    results = []

    print(f"Performance test: {URL}")
    print(f"Requests per level: {REQUESTS_PER_LEVEL}")
    print()

    for concurrency in CONCURRENCY_LEVELS:
        result = benchmark(concurrency)
        results.append(result)

        print(
            f"concurrency={result['concurrency']} "
            f"requests={result['requests']} "
            f"p50={result['p50_ms']:.2f}ms "
            f"p95={result['p95_ms']:.2f}ms "
            f"throughput={result['throughput_rps']:.2f} req/s"
        )

    with open("perf-results.md", "w", encoding="utf-8") as file:
        file.write("# Performance Results\n\n")
        file.write(f"Endpoint: `{URL}`\n\n")
        file.write(
            f"Requests per concurrency level: {REQUESTS_PER_LEVEL}\n\n"
        )
        file.write(
            "| Concurrency | Requests | p50 (ms) | p95 (ms) | Throughput (req/s) |\n"
        )
        file.write(
            "|---:|---:|---:|---:|---:|\n"
        )

        for result in results:
            file.write(
                f"| {result['concurrency']} "
                f"| {result['requests']} "
                f"| {result['p50_ms']:.2f} "
                f"| {result['p95_ms']:.2f} "
                f"| {result['throughput_rps']:.2f} |\n"
            )


if __name__ == "__main__":
    main()