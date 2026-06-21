from pybinbot import StandardResponse

from databases.web3_candidates import Web3CandidateTable


class Web3CandidateResponse(StandardResponse):
    data: Web3CandidateTable


class Web3CandidateListResponse(StandardResponse):
    data: list[Web3CandidateTable]
