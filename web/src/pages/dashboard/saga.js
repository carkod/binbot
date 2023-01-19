import { call, put, takeLatest } from "redux-saga/effects";
import request from "../../request";
import { GET_GAINERS_LOSERS, GET_GAINERS_LOSERS_SUCESS, GET_GAINERS_LOSERS_ERROR } from "./reducer";


export function getGainersLosers() {
    return {
        type: GET_GAINERS_LOSERS
    }
}

function getGainersLosersSucceeded(res) {
  return {
    type: GET_GAINERS_LOSERS_SUCESS,
    data: res.data,
  };
}

function getGainersLosersFailed(err) {
  return {
    type: GET_GAINERS_LOSERS_ERROR,
  };
}

/**
 * Get raw list 24hour ticker
 * of gainers and losers
 */
export function* getGainersLosersApi() {
  const requestURL = `${process.env.REACT_APP_GAINERS_LOSERS}`;
  try {
    const res = yield call(request, requestURL, "GET");
    yield put(getGainersLosersSucceeded(res));
  } catch (err) {
    yield put(getGainersLosersFailed(err));
  }
}

export function* watchGetGainersLosers() {
  yield takeLatest(GET_GAINERS_LOSERS, getGainersLosersApi);
}
