export default class Constants {
  static PUSHY_TOKEN = 'pushy_token';

  static UNAUTH_STATUS_CODE = 401;

  static CSRF_TOKEN = 'csrftoken';

  static TAB_NAMES = {
    uploads: 'uploads',
    invoices: 'invoices',
    credit_request: 'credit_requests',
    payments: 'payments',
    purchased_items: 'purchased_items',
  };

  static ROOT_LOGIN_PAGE = 'Login';

  static NON_SSO_USER_ERROR = 'This user is not registered as an SSO user. Please sign in with your Plate IQ password or contact your administrator.';

  static SSO_USER_ERROR = "This email is registered as an SSO user. To sign in with SSO, click on 'Sign in with SSO'.";

  static EMAIL_REQUIRED = 'Email is Required';

  static USERNAME_REQUIRED = 'Username is required';

  static PASSWORD_REQUIRED = 'Password is required';

  static ERROR = 'Error';

  static INCOMPLETE_SIGNIN = 'Unable to Complete Sign-in';

  static ERROR_COMMON = 'Something went wrong. Please try again later';
}
