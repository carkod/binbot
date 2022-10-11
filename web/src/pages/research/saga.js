import { call, put, takeLatest } from "redux-saga/effects";
import request, { buildBackUrl } from "../../request";
import { checkValue } from "../../validations";
import {
  addBlackListFailed,
  addBlackListSucceeded,
  ADD_BLACKLIST,
  deleteBlackListFailed,
  deleteBlackListSucceeded,
  DELETE_BLACKLIST,
  getBlacklistFailed,
  getBlacklistSucceeded,
  getResearchFailed,
  getResearchSucceeded,
  GET_BLACKLIST,
  GET_RESEARCH,
} from "./actions";

const baseUrl = buildBackUrl();

/**
 * Bots request/response handler
 */
export function* getResearchApi({ params }) {
  let url = new URL(process.env.REACT_APP_RESEARCH_SIGNALS, baseUrl);
  if (!checkValue(params)) {
    Object.keys(params).forEach((key) => {
      if (key === "order") {
        if (params["order"]) {
          params["order"] = 1;
        } else {
          params["order"] = -1;
        }
      }
      if (checkValue(params[key])) {
        delete params[key];
      } else {
        url.searchParams.append(key, params[key]);
      }
    });
  }
  try {
    const res = yield call(request, url.toString());
    yield put(getResearchSucceeded(res));
  } catch (err) {
    yield put(getResearchFailed(err));
  }
}

export function* watchResearchApi() {
  yield takeLatest(GET_RESEARCH, getResearchApi);
}

/**
 * Blacklist
 */
export function* getBlacklistApi() {
  let url = new URL(process.env.REACT_APP_RESEARCH_BLACKLIST, baseUrl);
  try {
    const res = yield call(request, url);
    yield put(getBlacklistSucceeded(res));
  } catch (err) {
    yield put(getBlacklistFailed(err));
  }
}

export function* watchGetBlacklistApi() {
  yield takeLatest(GET_BLACKLIST, getBlacklistApi);
}

/**
 * Add element to blacklist
 */
export function* addBlacklistApi({ data }) {
  const url = new URL(`${process.env.REACT_APP_RESEARCH_BLACKLIST}`, baseUrl);
  try {
    const res = yield call(request, url, "POST", data);
    yield put(addBlackListSucceeded(res));
  } catch (err) {
    yield put(addBlackListFailed(err));
  }
}

export function* watchAddBlacklistApi() {
  yield takeLatest(ADD_BLACKLIST, addBlacklistApi);
}

/**
 * Blacklist
 */
export function* deleteBlacklistApi({ pair }) {
  const url = `${process.env.REACT_APP_RESEARCH_BLACKLIST}/${pair}`;
  try {
    const res = yield call(request, url, "DELETE");
    yield put(deleteBlackListSucceeded(res));
  } catch (err) {
    yield put(deleteBlackListFailed(err));
  }
}

export function* watchDeleteBlackListApi() {
  yield takeLatest(DELETE_BLACKLIST, deleteBlacklistApi);
}
