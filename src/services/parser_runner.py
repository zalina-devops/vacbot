from concurrent.futures import ThreadPoolExecutor


def run_parsers(parsers, query):

    results = []

    with ThreadPoolExecutor(
        max_workers=len(parsers)
    ) as executor:

        futures = [
            executor.submit(
                parser.fetch,
                query
            )
            for parser in parsers
        ]

        for future in futures:

            try:
                results.extend(
                    future.result()
                )
            except Exception:
                pass

    return results