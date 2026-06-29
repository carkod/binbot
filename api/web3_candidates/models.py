from pydantic import BaseModel

from api.databases.web3_candidates import Web3CandidateTable


class Web3CandidateResponse(BaseModel):
    message: str
    detail: Web3CandidateTable


class Web3CandidateListResponse(BaseModel):
    message: str
    detail: list[Web3CandidateTable]
