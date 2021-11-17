import { call, put, takeLatest } from "redux-saga/effects";
import request, { defaultOptions } from "../../request";
import { checkValue } from "../../validations";
import {
  addBlackListFailed,
  addBlackListSucceeded,
  ADD_BLACKLIST,
  deleteBlackListFailed,
  deleteBlackListSucceeded,
  DELETE_BLACKLIST,
  editSettingsFailed,
  editSettingsSucceeded,
  EDIT_SETTINGS,
  getBlacklistFailed,
  getBlacklistSucceeded,
  getHistoricalResearchDataFailed,
  getHistoricalResearchDataSucceeded,
  getResearchFailed,
  getResearchSucceeded,
  getSettingsFailed,
  getSettingsSucceeded,
  GET_BLACKLIST,
  GET_HISTORICAL_RESEARCH,
  GET_RESEARCH,
  GET_SETTINGS,
} from "./actions";

/**
 * Bots request/response handler
 */
export function* getResearchApi({ params }) {
  let url = new URL(process.env.REACT_APP_RESEARCH_SIGNALS)
  if (!checkValue(params)) {
    Object.keys(params).forEach(key => {
      if (key === "order") {
        if (params["order"]) {
          params["order"] = 1
        } else {
          params["order"] = -1
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
    const res = yield call(request, url.toString(), defaultOptions);
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



/**
 * Blacklist
 */
 export function* getBlacklistApi() {
  let url = new URL(process.env.REACT_APP_RESEARCH_BLACKLIST)
  try {
    const res = yield call(request, url, defaultOptions);
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
 export function* addBlacklistApi({data}) {
  const url = new URL(`${process.env.REACT_APP_RESEARCH_BLACKLIST}`)
  defaultOptions.method = "POST";
  defaultOptions.body = JSON.stringify(data);
  try {
    const res = yield call(request, url, defaultOptions);
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
  const url = `${process.env.REACT_APP_RESEARCH_BLACKLIST}/${pair}`
  defaultOptions.method = "DELETE";
  try {
    const res = yield call(request, url, defaultOptions);
    yield put(deleteBlackListSucceeded(res));
  } catch (err) {
    yield put(deleteBlackListFailed(err));
  }
}

export function* watchDeleteBlackListApi() {
  yield takeLatest(DELETE_BLACKLIST, deleteBlacklistApi);
}

/**
 * Settings (controller)
 */
 export function* getSettingsApi() {
  const url = new URL(process.env.REACT_APP_RESEARCH_CONTROLLER)
  try {
    const res = yield call(request, url, defaultOptions);
    yield put(getSettingsSucceeded(res));
  } catch (err) {
    yield put(getSettingsFailed(err));
  }
}

export function* watchGetSettingsApi() {
  yield takeLatest(GET_SETTINGS, getSettingsApi);
}


/**
 * Edit Settings (controller)
 */
 export function* editSettingsApi({ data }) {
  const url = new URL(process.env.REACT_APP_RESEARCH_CONTROLLER)
  defaultOptions.method = "PUT";
  defaultOptions.body = JSON.stringify(data);
  try {
    const res = yield call(request, url, defaultOptions);
    yield put(editSettingsSucceeded(res));
  } catch (err) {
    yield put(editSettingsFailed(err));
  }
}

export function* watchEditSettingsApi() {
  yield takeLatest(EDIT_SETTINGS, editSettingsApi);
}