import Mixpanel from 'react-native-mixpanel';
import { MIXPANEL_TOKEN } from 'react-native-dotenv';

export const setUpMixpanel = async () => {
  if (MIXPANEL_TOKEN) {
    Mixpanel.sharedInstanceWithToken(MIXPANEL_TOKEN);
  }
};

export const sendMixpanelEvent = async (event_name, properties) => {
  if (MIXPANEL_TOKEN) {
    if (properties) {
      const newProperties = JSON.parse(JSON.stringify(properties));
      Mixpanel.trackWithProperties(event_name, newProperties);
    } else {
      Mixpanel.track(event_name);
    }
  }
};

export const setMixpanelUser = async (user) => {
  if (user && MIXPANEL_TOKEN) {
    const {
      username, email, id, first_name, last_name, role, siteVersion, date_joined
    } = user;
    let { optional_features, preferences } = user;
    const featureFlags = [];
    const featurePreferences = [];

    if (!optional_features) optional_features = {};
    if (!preferences) preferences = {};
    Object.keys(optional_features).forEach((key) => {
      if (optional_features[key].enabled) featureFlags.push(key);
    });

    Object.keys(preferences).forEach((key) => {
      if (preferences[key].enabled) featurePreferences.push(key);
    });

    if (email) {
      Mixpanel.identify(` ${email}`);
      Mixpanel.setOnce({
        username,
        Identity: id,
        Name: `${first_name} ${last_name}`,
        Email: email,
        Role: role,
        'Site Version': siteVersion,
        'Date Joined': date_joined,
        'Feature Flags': featureFlags,
        Preferences: featurePreferences,
      });
    }

    Mixpanel.registerSuperProperties({ username });
  }
};

export const removeMixpanelUser = async () => {
  if (MIXPANEL_TOKEN) {
    Mixpanel.clearSuperProperties();
  }
};

export const MixpanelEvents = {
  APP_LAUNCHED: 'App Launched',
  USER_LOGGED_IN: 'User Logged In',
  USER_LOGGED_OUT: 'User Logged Out',
  UPLOAD_TAB_OPENED: 'Upload Tab Opened',
  INVOICE_UPLOADED: 'Invoice Uploaded',
  INVOICES_TAB_OPENED: 'Invoices Tab Opened',
  INVOICES_FILTERED: 'Invoices Filtered',
  INVOICES_SEARCHED: 'Invoices Searched',
  INVOICE_OPENED: 'Invoice Opened',
  INVOICE_APPROVED: 'Invoice Approved',
  INVOICE_FLAGGED: 'Invoice Flagged',
  INVOICE_ITEMS_OPENED: 'Invoice Items Opened',
  INVOICE_GL_SPLITS_OPENED: 'Invoice GL Splits Opened',
  INVOICE_IMAGES_OPENED: 'Invoice Images Opened',
  INVOICE_HISTORY_OPENED: 'Invoice History Opened',
  INVOICE_IMAGE_SELECTED: 'Invoice Image Selected',
  INVOICE_DELETED: 'Invoice Deleted',

  CREDIT_REQUESTS_TAB_OPENED: 'Credit Requests Tab Opened',
  CREDIT_REQUESTS_FLAGGED: 'Credit Requests Flagged',
  CREDIT_REQUESTS_FILTERED: 'Credit Requests Filtered',
  CREDIT_REQUESTS_SEARCHED: 'Credit Requests Searched',
  CREDIT_REQUEST_OPENED: 'Credit Request Opened',
  CREDIT_REQUEST_ITEMS_OPENED: 'Credit Request Items Opened',
  CREDIT_REQUEST_GL_SPLITS_OPENED: 'Credit Request GL Splits Opened',
  CREDIT_REQUEST_IMAGES_OPENED: 'Credit Request Images Opened',
  CREDIT_REQUEST_HISTORY_OPENED: 'Credit Request History Opened',
  CREDIT_REQUEST_IMAGE_SELECTED: 'Credit Request Image Selected',
  CREDIT_REQUESTS_CREATED: 'Credit Requests Created',

  PAYMENT_TAB_OPENED: 'Payments Tab Opened',
  PAYMENT_FILTERED: 'Payments Filtered',
  PAYMENT_SEARCHED: 'Payments Searched',
  PAYMENT_OPENED: 'Payment Opened',
  PAYMENT_APPROVED: 'Payment Approved',
  PAYMENT_INVOICES_OPENED: 'Payment Invoices Opened',
  PAYMENT_CHECK_STUBS_OPENED: 'Payment Check Stubs Opened',
  PAYMENT_CHECK_STUB_SELECTED: 'Payment Check Stub Selected',

  ITEMS_TAB_OPENED: 'Items Tab Opened',
  ITEMS_FILTERED: 'Items Filtered',
  ITEMS_SEARCHED: 'Items Searched',
  ITEMS_OPENED: 'Items Opened',
  ITEMS_CHART_OPENED: 'Items Chart Opened',
  ITEMS_INVOICE_OPENED: 'Items Invoice Opened',
  ITEM_STARRED: 'Item Starred',
  ITEM_STAR_DELETED: 'Item Star Deleted',
};
