import { combineReducers } from 'redux';
import AuthReducer from './auth/AuthReducer';
import PendingApprovalReducer from './invoices/PendingApprovalReducer';
import AllInvoiceReducer from './invoices/AllInvoiceReducer';
import VendorReducer from './vendors/VendorReducer';
import PendingUploadReducer from './uploads/PendingUploadReducer';
import InvoiceDetailReducer from './invoices/InvoiceDetailReducer';
import PendingPaymentApprovalReducer from './payments/PendingPaymentApprovalReducer';
import AllPaymentReducer from './payments/AllPaymentReducer';
import PaymentDetailReducer from './payments/PaymentDetailReducer';
import MfaReducer from './auth/MfaReducer';
import UserInfoReducer from './auth/UserInfoReducer';
import RestaurantUsersReducer from './restaurants/RestaurantUsersReducer';
import OAuthReducer from './auth/OAuthReducer';
import OAuthMfaReducer from './auth/OAuthMfaReducer';
import SSOReducer from './auth/SSOReducer';
import AllCreditRequestReducer from './credit_requests/AllCreditRequestReducer';
import CreditRequestDetailReducer from './credit_requests/CreditRequestDetailReducer';
import AddCreditRequestReducer from './credit_requests/AddCreditRequestReducer';
import AllPurchasedItemsReducer from './purchased_items/AllPurchasedItemsReducer';
import PurchasedItemDetailReducer from './purchased_items/PurchasedItemDetailReducer';
import StarredPurchasedItemsReducer from './purchased_items/StarredPurchasedItemsReducer';
import CategoriesReducer from './categories/CategoriesReducer';
import AllTransactionReducer from './transactions/AllTransactionReducer';
import TransactionDetailReducer from './transactions/TransactionDetailReducer';
import PendingReceiptTransactionReducer from './transactions/PendingReceiptTransactionReducer';
import PendingTransactionUploadReducer from './transactions/PendingTransactionUploadReducer';
import TransactionUnassignedReceiptReducer from './transactions/TransactionUnassignedReceiptReducer';

export default combineReducers({
  auth: AuthReducer,
  oauth: OAuthReducer,
  mfa: MfaReducer,
  oauthMfa: OAuthMfaReducer,
  sso: SSOReducer,
  userInfo: UserInfoReducer,
  pendingInvoices: PendingApprovalReducer,
  allInvoices: AllInvoiceReducer,
  vendors: VendorReducer,
  pendingUploads: PendingUploadReducer,
  invoiceDetail: InvoiceDetailReducer,
  pendingPayments: PendingPaymentApprovalReducer,
  allPayments: AllPaymentReducer,
  paymentDetail: PaymentDetailReducer,
  restaurantUsers: RestaurantUsersReducer,
  allCreditRequests: AllCreditRequestReducer,
  creditRequestDetail: CreditRequestDetailReducer,
  addCreditRequest: AddCreditRequestReducer,
  starredPurchasedItems: StarredPurchasedItemsReducer,
  allPurchasedItems: AllPurchasedItemsReducer,
  purchasedItemDetail: PurchasedItemDetailReducer,
  categories: CategoriesReducer,
  allTransactions: AllTransactionReducer,
  transactionDetail: TransactionDetailReducer,
  pendingReceiptTransactions: PendingReceiptTransactionReducer,
  pendingTransactionReceipts: PendingTransactionUploadReducer,
  unassignedReceipts: TransactionUnassignedReceiptReducer,
});
