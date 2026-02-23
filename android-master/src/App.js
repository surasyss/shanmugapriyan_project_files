/**
 * Sample React Native MainRouter
 * https://github.com/facebook/react-native
 *
 * @format
 * @flow
 */

import React from 'react';
import { Provider } from 'react-redux';
import { enableScreens } from 'react-native-screens';

import store from './store';
import MainRouter from './routers/MainRouter';
import SimpleToast from './components/Global/SimpleToast';
import WarningToast from './components/Global/WarningToast';
import ErrorToast from './components/Global/ErrorToast';
import SuccessToast from './components/Global/SuccessToast';

// eslint-disable-next-line no-console
console.disableYellowBox = true;
enableScreens();

// eslint-disable-next-line react/prefer-stateless-function
class App extends React.Component {
  render() {
    return (
      <Provider store={store}>
        <MainRouter />
        <SimpleToast />
        <WarningToast />
        <ErrorToast />
        <SuccessToast />

      </Provider>
    );
  }
}

export default App;
