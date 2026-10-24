from .engine import build_index

if __name__ == "__main__":
    print(build_index(lambda msg: print(msg, flush=True)), flush=True)
