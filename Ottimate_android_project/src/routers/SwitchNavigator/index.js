import React from 'react';
import { createAppContainer, createSwitchNavigator } from 'react-navigation';
import { createStackNavigator } from 'react-navigation-stack';
import { fromBottom, fromRight, fromTop } from 'react-navigation-transitions';
import { Image, TouchableOpacity } from 'react-native';
import { createBottomTabNavigator } from 'react-navigation-tabs';
import {
  LoginContainer,
  MfaContainer,
  OAuthLoginContainer,
  OAuthMfaContainer,
  SSOLoginContainer,
  LoadUserInfoContainer,
  UploadInvoiceContainer,
  InvoicePreviewContainer,
  DeleteInvoiceContainer,
  InvoiceDetailContainer,
  InvoiceDetailStaticContainer,
  PaymentDetailContainer,
  CreditRequestDetailContainer,
  VendorPickerContainer,
  AllPurchasedItemsContainer,
  PurchasedItemDetailContainer, CategoryPickerContainer, AllTransactionsContainer, TransactionDetailContainer,
  PendingReceiptContainer, ReceiptCameraContainer, ReceiptPreviewContainer
} from '../../containers';
import Colors from '../../styles/Colors';
import styles from './styles';
import Splash from '../../components/Auth/Splash';
import InvoiceCamera from '../../components/Upload/InvoiceCamera';
import ApprovalInvoices from '../../components/Invoices/ApprovalInvoices';
import InvoiceDetailImage from '../../components/Invoices/InvoiceDetailImage';
import ApprovalPayments from '../../components/Payments/ApprovalPayments';
import CreditRequests from '../../components/CreditRequests/CreditRequests';
import RestaurantPicker from '../../components/Global/RestaurantPicker';
import More from '../../components/More/More';
import Images from '../../styles/Images';
import MainAppRoute from '../MainAppRouter';
import Constants from '../../utils/Constants';

const headerStyle = {
  headerBackTitle: null,
  headerStyle: styles.headerStyle,
  headerTitleStyle: styles.headerTitleStyle,
  headerTintColor: Colors.white,
};

const logoutHeader = {
  headerLeft: (
    <TouchableOpacity onPress={() => {
      global.showLogout(true);
    }}
    >
      <Image
        source={Images.user}
        style={styles.logoutIcon}
        resizeMode="contain"
      />
    </TouchableOpacity>
  )
};

const handleCustomTransition = (nav) => {
  const { scenes } = nav;
  const prevScene = scenes[scenes.length - 2];
  const nextScene = scenes[scenes.length - 1];

  // Custom transitions go there
  if (prevScene
      && prevScene.route.routeName === 'InvoiceDetail'
      && nextScene.route.routeName === 'InvoiceDetail') {
    if (prevScene.route.params.index < nextScene.route.params.index) { return fromBottom(500); }
    return fromTop(500);
  }

  if (prevScene
      && prevScene.route.routeName === 'PaymentDetail'
      && nextScene.route.routeName === 'PaymentDetail') {
    if (prevScene.route.params.index < nextScene.route.params.index) { return fromBottom(500); }
    return fromTop(500);
  }

  if (prevScene
      && prevScene.route.routeName === 'CreditRequestDetail'
      && nextScene.route.routeName === 'CreditRequestDetail') {
    if (prevScene.route.params.index < nextScene.route.params.index) { return fromBottom(500); }
    return fromTop(500);
  }

  if (prevScene
      && prevScene.route.routeName === 'PurchasedItemDetail'
      && nextScene.route.routeName === 'PurchasedItemDetail') {
    if (prevScene.route.params.index < nextScene.route.params.index) { return fromBottom(500); }
    return fromTop(500);
  }

  if (prevScene
      && prevScene.route.routeName === 'TransactionDetail'
      && nextScene.route.routeName === 'TransactionDetail') {
    if (prevScene.route.params.index < nextScene.route.params.index) { return fromBottom(500); }
    return fromTop(500);
  }

  return fromRight();
};

const DashboardStack = createStackNavigator({
  UploadInvoice: {
    screen: UploadInvoiceContainer,
    navigationOptions: () => ({
      ...headerStyle, ...logoutHeader,
    })
  },
  InvoiceCamera: {
    screen: InvoiceCamera,
    navigationOptions: () => ({
      header: null
    })
  },
  InvoicePreview: {
    screen: InvoicePreviewContainer,
    navigationOptions: () => (headerStyle)
  },
  DeleteInvoice: {
    screen: DeleteInvoiceContainer,
    navigationOptions: () => ({
      header: null
    })
  },
  PendingReceipts: {
    screen: PendingReceiptContainer,
    navigationOptions: () => (headerStyle)
  },
  ReceiptPreviewPage: {
    screen: ReceiptPreviewContainer,
    navigationOptions: () => ({
      header: null
    })
  },
  ReceiptCamera: {
    screen: ReceiptCameraContainer,
    navigationOptions: () => ({
      header: null
    })
  },
}, {
  initialRouteName: 'UploadInvoice',
  headerLayoutPreset: 'center',
});

DashboardStack.navigationOptions = ({ navigation }) => {
  let tabBarVisible = true;
  if (navigation.state.index > 0) {
    tabBarVisible = false;
  }
  return {
    tabBarVisible,
  };
};

const InvoicesStack = createStackNavigator({
  Invoices: {
    screen: ApprovalInvoices,
    navigationOptions: () => ({
      ...headerStyle, ...logoutHeader,
    })
  },
  InvoiceDetail: {
    screen: InvoiceDetailContainer,
    navigationOptions: () => ({
      headerBackTitle: null,
      headerTitleStyle: styles.headerLeftTitle,
    })
  },
  InvoiceDetailStatic: {
    screen: InvoiceDetailStaticContainer
  },
  InvoiceDetailImage: {
    screen: InvoiceDetailImage,
    navigationOptions: () => ({
      headerBackTitle: null,
      headerTitleStyle: styles.headerSmallTitleStyle,
    })
  }
}, {
  initialRouteName: 'Invoices',
  headerLayoutPreset: 'center',
  transitionConfig: (nav) => handleCustomTransition(nav),
});

InvoicesStack.navigationOptions = ({ navigation }) => {
  let tabBarVisible = true;
  if (navigation.state.index > 0) {
    tabBarVisible = false;
  }
  return {
    tabBarVisible,
  };
};

const PaymentsStack = createStackNavigator({
  Payments: {
    screen: ApprovalPayments,
    navigationOptions: () => ({
      ...headerStyle, ...logoutHeader,
    })
  },
  PaymentDetail: {
    screen: PaymentDetailContainer,
    navigationOptions: () => ({
      headerBackTitle: null,
      headerTitleStyle: styles.headerLeftTitle
    })
  },
  InvoiceDetailStatic: {
    screen: InvoiceDetailStaticContainer
  },
}, {
  initialRouteName: 'Payments',
  headerLayoutPreset: 'center',
  transitionConfig: (nav) => handleCustomTransition(nav),
});

PaymentsStack.navigationOptions = ({ navigation }) => {
  let tabBarVisible = true;
  if (navigation.state.index > 0) {
    tabBarVisible = false;
  }
  return {
    tabBarVisible,
  };
};

const creditStackVar = {
  CreditRequests: {
    screen: CreditRequests,
    navigationOptions: () => ({
      ...headerStyle, ...logoutHeader,
    })
  },
  CreditRequestDetail: {
    screen: CreditRequestDetailContainer,
    navigationOptions: () => ({
      headerBackTitle: null,
      headerTitleStyle: styles.headerLeftTitle
    })
  },
  RestaurantPicker: {
    screen: RestaurantPicker
  },
  VendorPicker: {
    screen: VendorPickerContainer
  },
};

const CreditsStack = createStackNavigator(creditStackVar, {
  initialRouteName: 'CreditRequests',
  headerLayoutPreset: 'center',
  transitionConfig: (nav) => handleCustomTransition(nav),
});

CreditsStack.navigationOptions = ({ navigation }) => {
  let tabBarVisible = true;
  if (navigation.state.index > 0) {
    tabBarVisible = false;
  }
  return {
    tabBarVisible,
  };
};

const ItemsStack = createStackNavigator({
  Items: {
    screen: AllPurchasedItemsContainer,
    navigationOptions: () => ({
      ...headerStyle, ...logoutHeader,
    })
  },
  PurchasedItemDetail: {
    screen: PurchasedItemDetailContainer,
    navigationOptions: () => ({
      headerBackTitle: null,
      headerTitleStyle: styles.headerLeftTitle
    })
  },
  CategoryPicker: {
    screen: CategoryPickerContainer
  },
  InvoiceDetailStatic: {
    screen: InvoiceDetailStaticContainer
  },
}, {
  initialRouteName: 'Items',
  headerLayoutPreset: 'center',
  transitionConfig: (nav) => handleCustomTransition(nav),
});

ItemsStack.navigationOptions = ({ navigation }) => {
  let tabBarVisible = true;
  if (navigation.state.index > 0) {
    tabBarVisible = false;
  }
  return {
    tabBarVisible,
  };
};

const transactionStack = {
  Transactions: {
    screen: AllTransactionsContainer,
    navigationOptions: () => ({
      ...headerStyle, ...logoutHeader,
    })
  },
  TransactionDetail: {
    screen: TransactionDetailContainer,
    navigationOptions: () => ({
      headerBackTitle: null,
      headerTitleStyle: styles.headerLeftTitle
    })
  },
  ReceiptPreviewPage: {
    screen: ReceiptPreviewContainer,
    navigationOptions: () => ({
      header: null
    })
  },
  ReceiptCamera: {
    screen: ReceiptCameraContainer,
    navigationOptions: () => ({
      header: null
    })
  },
};

const TransactionsStack = createStackNavigator(transactionStack, {
  initialRouteName: 'Transactions',
  headerLayoutPreset: 'center',
  transitionConfig: (nav) => handleCustomTransition(nav),
});

TransactionsStack.navigationOptions = ({ navigation }) => {
  let tabBarVisible = true;
  if (navigation.state.index > 0) {
    tabBarVisible = false;
  }
  return {
    tabBarVisible,
  };
};

const MoreStack = createStackNavigator({
  More: {
    screen: More,
  },
}, {
  initialRouteName: 'More',
  transitionConfig: (nav) => handleCustomTransition(nav),
});

MoreStack.navigationOptions = ({ navigation }) => {
  let tabBarVisible = true;
  if (navigation.state.index > 0) {
    tabBarVisible = false;
  }
  return {
    tabBarVisible,
  };
};

const AuthStack = createStackNavigator({
  Login: {
    screen: LoginContainer,
    navigationOptions: () => ({
      header: null
    })
  },
  OAuthLogin: {
    screen: OAuthLoginContainer,
    navigationOptions: () => ({
      header: null
    })
  },
  SSOLogin: {
    screen: SSOLoginContainer,
    navigationOptions: () => ({
      header: null
    })
  },
  Mfa: {
    screen: MfaContainer,
    navigationOptions: () => (headerStyle)
  },
  OAuthMfa: {
    screen: OAuthMfaContainer,
    navigationOptions: () => (headerStyle)
  },
  LoadUserInfo: {
    screen: LoadUserInfoContainer,
    navigationOptions: () => ({
      header: null
    })
  },
}, {
  initialRouteName: Constants.ROOT_LOGIN_PAGE,
});

export const mainNavigatorTabs = {
  uploads: {
    screen: DashboardStack,
    key: 'DashboardStack',
    label: 'Home',
    icon: Images.tab_camera_unselected,
  },
  invoices: {
    screen: InvoicesStack,
    key: 'InvoicesStack',
    label: 'Invoices',
    icon: Images.tab_invoices,
  },
  payments: {
    screen: PaymentsStack,
    key: 'PaymentsStack',
    label: 'Payments',
    icon: Images.tab_payment_icon,
  },
  credit_request: {
    screen: CreditsStack,
    key: 'CreditsStack',
    label: 'Credits',
    icon: Images.icon_credit_requests,
  },
  items: {
    screen: ItemsStack,
    key: 'ItemsStack',
    label: 'Items',
    icon: Images.ic_items,
  },
  transactions: {
    screen: TransactionsStack,
    key: 'TransactionsStack',
    label: 'Transactions',
    icon: Images.ic_transactions,
  },
  more: {
    screen: MoreStack,
    key: 'MoreStack',
    label: 'More',
    icon: Images.ic_more,
  }
};

const Tabs = {};
Object.keys(mainNavigatorTabs).forEach((jsonKey) => {
  const tab = mainNavigatorTabs[jsonKey];
  const { screen, key, label } = tab;
  Tabs[key] = {
    screen,
    navigationOptions: () => ({
      tabBarLabel: label,
    })
  };
});

const TabNavigator = createBottomTabNavigator(
  Tabs,
  {
    initialRouteName: 'DashboardStack',
    tabBarOptions: {
      activeTintColor: Colors.sent,
      tabStyle: {},
    },
    tabBarComponent: (props) => (
      <MainAppRoute {...props} />
    ),
    defaultNavigationOptions: ({ navigation }) => ({
      // eslint-disable-next-line no-unused-vars
      tabBarIcon: ({ focused, horizontal, tintColor }) => {
        const { routeName } = navigation.state;
        let image;
        if (routeName === 'DashboardStack') {
          image = Images.tab_camera_unselected;
        } else if (routeName === 'InvoicesStack') {
          image = Images.tab_invoices;
        } else if (routeName === 'PaymentsStack') {
          image = Images.tab_payment_icon;
        } else if (routeName === 'CreditsStack') {
          image = Images.icon_credit_requests;
        } else if (routeName === 'ItemsStack') {
          image = Images.ic_items;
        } else if (routeName === 'TransactionsStack') {
          image = Images.ic_transactions;
        } else if (routeName === 'MoreStack') {
          image = Images.ic_more;
        }

        return (
          <Image
            source={image}
            style={focused ? styles.selectedIcon : styles.unselectedIcon}
          />
        );
      },
      tabBarOnPress: ({ navigation, defaultHandler }) => {
        if (navigation.state.routeName === 'MoreStack') {
          this.RBSheet.open();
          return;
        }
        defaultHandler();
      }
    })
  }
);

const SplashStack = createStackNavigator({
  Splash
}, {
  initialRouteName: 'Splash',
  headerMode: 'none',
  navigationOptions: {
    headerVisible: false,
  }
});

const AppNavigator = createSwitchNavigator(
  {
    Auth: AuthStack,
    App: TabNavigator,
    SplashStack
  },
  {
    initialRouteName: 'SplashStack'
  }
);

export default createAppContainer(AppNavigator);
