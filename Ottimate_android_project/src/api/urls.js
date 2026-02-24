export default class Urls {
    // LOGIN URL
    static LOGIN = 'auth/token/';

    static OAUTH_LOGIN = 'oauth/authorize/';

    static SSO_LOGIN = 'sso/login/info/';

    static USER_INFO = 'user/me/';

    static RESTAURANTS = 'restaurant/';

    static COMPANIES = 'accounting/company/';

    static PUSH_TOKEN = 'push_token/';

    static DELETE_PUSH_TOKEN = 'push_token/:device_id/';

    static OAUTH_TOKEN = 'oauth/token/';

    // INVOICES URL
    static INVOICES = 'invoice/';

    static INVOICE_DETAILS = 'invoice/:invoice_id/';

    static INVOICE_LINE_ITEMS = 'invoice/:invoice_id/line_items/';

    static INVOICE_GL_SPLITS = 'invoice/:invoice_id/gl_splits/';

    static INVOICE_IMAGES = 'invoice/:invoice_id/images/';

    static INVOICE_HISTORY = 'invoice/:invoice_id/history/';

    static APPROVE_INVOICE = 'invoice/:invoice_id/approve/';

    static ADD_INVOICE_FLAG = 'invoice/:invoice_id/flag/';

    static RESOLVE_INVOICE_FLAG = 'invoice/:invoice_id/resolve/';

    static SHARE_TEXT_INVOICE = 'invoice/:invoice_id/shareable_data/';

    // VENDORS URL
    static VENDORS = 'vendor/';

    // RESTAURANTS URL

    static RESTAURANT_USERS = 'restaurant/:restaurant_id/users/';

    // UPLOAD URL
    static S3SIGNURL = 'invoice/s3sign/';

    // PAYMENTS URL
    static PAYMENTS = 'billpay/cheque/';

    static APPROVE_PAYMENT = 'billpay/cheque/:payment_id/approve/';

    // PURCHASED ITEMS

    static PURCHASED_ITEMS = 'integration/purchased_item/list_grouped/';

    static PURCHASED_ITEM_DETAIL = 'integration/purchased_item/:item_id/';

    static PURCHASED_ITEM_TREND = 'analytics/trends/purchased_item/:item_id/';

    static PURCHASED_ITEM = 'integration/purchased_item/:item_id/';

    static STAR_PURCHASED_ITEM = 'integration/purchased_item/:item_id/star/';

    // CATEGORIES

    static CATEGORIES = 'category/';

    // TRANSACTIONS
    static TRANSACTIONS = 'v0/transaction/';

    static TRANSACTION_DETAIL = 'v0/transaction/:transaction_id/';

    static TRANSACTION_RECEIPT = 'v0/transaction-receipt/?company=:company_id';

    static S3_SIGN_TRANSACTION = 'v0/s3sign/';

    static UNASSIGNED_RECEIPTS = 'v0/receipt/';

    static ADD_MEMO = `${this.TRANSACTION_DETAIL}memo/?company=:company_id`;

    // FORCE UPDATE URL
    static FORCE_UPDATE = 'app/update/force/?client=android&version='
}
