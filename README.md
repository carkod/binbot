## Logic to compare with currently held asset

1. If currently held asset oscillator strength > buy signal asset
    return false, restart long_algo
2. Else
    run default code

Deploy first version of app

## Global mechanism 

1. Execute Sell Algorithm
2. If True, execute Sell Order
3. If False, re run Sell Algorithm


1. Execute Buy Algorithm
2. If True
    a. Sell current funds to buy new asset?
        a1. Stop purchase
        a2. True, continue with b

    b. Cannot sell because:
        b1. Exit
        b2. Rerun buy and sell algo

3. Resolve situation where 2 algorithms collide.


# Installation

This repo uses an automated system to sync all local development code with production code

Pushing to master will trigger update on production server.

Develop on development branch, when details are finilized, push to master to update production code.

