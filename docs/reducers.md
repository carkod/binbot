## When make use of redux state?
Over time, the development of the front-end app made the application larger due to the amount of API calls that the application uses. So Redux is used to share application data and state.

With the new redux-toolkit, a lot of boilerplate code has been removed. No need for action creators, mapping of reducers, props and states.

1. Everytime a new API endpoint is available for the web app:
  - Create a new xxApiSlice by injection using `userApiSlice`. Check out the other slices such as `botApiSlice`

2. If application state is neede (which with react-toolkit it is not anymore)
- Create a xxAppSlice. Checkout `botSlice`

However, because some operations require quick readonly data that needs to be up to date, in some situations it's not worth doing all above steps and writing so much code for data that doesn't even change, so some components may have a `requests.js`, which is where we simply make calls to API endpoints and get the json.


## How to debug redux state in this app
### Find the API endpoint called
1. In the component find the props that return the data e.g. `this.props.balance`
2. Find the name of the reducer in the `mapStateToProps` function e.g. `state.balanceReducer`
3. Find this constant in the saga e.g. `watchGbpBalanceApi`
4. In the generator function e.g. `getBalanceAll` you will find the `requestUrl`
5. This URL will have a constant variable which is usually located in the `env`