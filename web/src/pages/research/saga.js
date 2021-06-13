import { call, put, takeLatest } from "redux-saga/effects";
import request, { defaultOptions } from "../../request";
import {
  getResearchFailed,
  getResearchSucceeded,
  GET_RESEARCH,
} from "./actions";

/**
 * Bots request/response handler
 */
export function* getResearchApi() {
  const requestURL = process.env.REACT_APP_RESEARCH_SIGNALS;
  try {
    const res = yield call(request, requestURL, defaultOptions);
    yield put(getResearchSucceeded(res));
  } catch (err) {
    yield put(getResearchFailed(err));
  }
}

export function* watchResearchApi() {
  yield takeLatest(GET_RESEARCH, getResearchApi);
}
