from streaming.strategies.base import LifecyclePolicy
from streaming.strategies.default import DefaultLifecycleStrategy


class BuyTheDipLifecycleStrategy(DefaultLifecycleStrategy):
    algorithm_names = frozenset({"coinrule_buy_the_dip"})
    policy = LifecyclePolicy(block_reversal_after_loss=True)
