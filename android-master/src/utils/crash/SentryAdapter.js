import * as Sentry from '@sentry/react-native';
import { SENTRY_TOKEN } from 'react-native-dotenv';
import Adapter from '../Adapter';

// eslint-disable-next-line import/prefer-default-export
export const setupSentry = async () => {
  if (SENTRY_TOKEN) {
    const user = await Adapter.getUser();

    Sentry.init({
      dsn: SENTRY_TOKEN
    });

    if (user) {
      Sentry.setTag('user_id', user.id);
      Sentry.setTag('user_username', user.username);
      Sentry.setTag('user_name', user.display_name);
      Sentry.setTag('user_email', user.email);
    }
  }
};
