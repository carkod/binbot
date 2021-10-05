# Why does this project have no tests?

I believe unit tests in front-end are not required in this project. Front-end applications are created to facilitate users work with a nice, easy to use interface. Covering every line of code with unit tests does not help adding value to the final user.

Also, there isn't usually complex computations in front-end, most of the time, we either render data in a template or call an API endpoint that will already digest most of the complexity, as it can be quite slow to do it in the browser.

Instead of using unit tests in front-end, Typescript type guards should be used to minimize the impact of regressions and bugs.

End to end tests should be considered. Unit tests should be considered only in API application.