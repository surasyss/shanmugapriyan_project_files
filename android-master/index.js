/**
 * @format
 */

import { AppRegistry } from 'react-native';
import { name as appName } from './app.json';
import App from './src/App';
import { setupSentry } from './src/utils/crash/SentryAdapter';
import { setUpMixpanel } from './src/utils/mixpanel/MixPanelAdapter';

setupSentry();
setUpMixpanel();

AppRegistry.registerComponent(appName, () => App);

// eslint-disable-next-line no-undef
if (!__DEV__) {
  // eslint-disable-next-line no-console
  console.log = () => {};
}
