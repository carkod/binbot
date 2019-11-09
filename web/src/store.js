import { createStore, applyMiddleware } from 'redux'
import createSagaMiddleware from 'redux-saga'
import rootSagas from './sagas'
import rootReducer from './reducer'

export default function configureStore() {
  const sagaMiddleware = createSagaMiddleware()
  const store = createStore(
    rootReducer,
    applyMiddleware(sagaMiddleware)
  )
  sagaMiddleware.run(rootSagas)
  return store;
}