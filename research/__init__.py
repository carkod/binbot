from signals import ResearchSignals
from new_tokens import NewTokens
import threading


if __name__ == "__main__":
    # Research market updates
    nt = NewTokens()
    new_tokens_thread = threading.Thread(
        name="new_tokens_thread", target=nt.run
    )
    new_tokens_thread.start()

    rs = ResearchSignals()
    rs_thread = threading.Thread(
        name="rs_thread", target=rs.start_stream
    )
    rs_thread.start()
