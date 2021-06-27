import { call, put, takeLatest } from "redux-saga/effects";
import request, { defaultOptions } from "../../request";
import { checkValue } from "../../validations";
import {
  getHistoricalResearchDataFailed,
  getHistoricalResearchDataSucceeded,
  getResearchFailed,
  getResearchSucceeded,
  GET_HISTORICAL_RESEARCH,
  GET_RESEARCH,
} from "./actions";

/**
 * Bots request/response handler
 */
export function* getResearchApi({ params }) {
  let url = new URL(process.env.REACT_APP_RESEARCH_SIGNALS)
  if (!checkValue(params)) {
    url.search = new URLSearchParams(params).toString()
  }
  try {
    const res = yield call(request, url, defaultOptions);
    yield put(getResearchSucceeded(res));
  } catch (err) {
    yield put(getResearchFailed(err));
  }
}

export function* watchResearchApi() {
  yield takeLatest(GET_RESEARCH, getResearchApi);
}


/**
 * Historical research data
 */
 export function* getHistoricalResearchApi({ params }) {
  let url = new URL(process.env.REACT_APP_RESEARCH_HISTORICAL_SIGNALS)
  if (!checkValue(params)) {
    url.search = new URLSearchParams(params).toString()
  }
  try {
    const res = yield call(request, url, defaultOptions);
    yield put(getHistoricalResearchDataSucceeded(res));
  } catch (err) {
    yield put(getHistoricalResearchDataFailed(err));
  }
}

export function* watchHistoricalResearchApi() {
  yield takeLatest(GET_HISTORICAL_RESEARCH, getHistoricalResearchApi);
}