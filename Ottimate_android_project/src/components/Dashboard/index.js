import React, { Component } from 'react';
import { View, Image } from 'react-native';
import { BottomNavigation } from 'react-native-paper';
import styles from './styles';
import Colors from '../../styles/Colors';

import Logout from '../Auth/Logout';
import ApprovalInvoices from '../Invoices/ApprovalInvoices';
import UploadInvoiceContainer from '../../containers/Upload/UploadInvoiceContainer';
import { MixpanelEvents, sendMixpanelEvent } from '../../utils/mixpanel/MixPanelAdapter';
import Images from '../../styles/Images';
import ApprovalPayments from '../Payments/ApprovalPayments';
import Constants from '../../utils/Constants';
import CreditRequests from '../CreditRequests/CreditRequests';
import AllPurchasedItemsContainer from '../../containers/PurchasedItems/AllPurchasedItemsContainer';

export default class Dashboard extends Component {
  constructor(props) {
    super(props);
    this.state = {
      index: 0,
    };
  }

  onTabPress(props) {
    const { setTitle } = this.props;
    if (props.route.key === Constants.TAB_NAMES.uploads) setTitle('Upload');
    else if (props.route.key === Constants.TAB_NAMES.invoices) setTitle('Invoices');
    else if (props.route.key === Constants.TAB_NAMES.credit_request) setTitle('Credits');
    else if (props.route.key === Constants.TAB_NAMES.payments) setTitle('Payments');
    else if (props.route.key === Constants.TAB_NAMES.purchased_items) setTitle('Items');
  }

  getIcon(key) {
    if (key === Constants.TAB_NAMES.uploads) return Images.tab_camera_unselected;
    if (key === Constants.TAB_NAMES.invoices) return Images.tab_invoices;
    if (key === Constants.TAB_NAMES.credit_request) return Images.icon_credit_requests;
    if (key === Constants.TAB_NAMES.payments) return Images.tab_payment_icon;
    if (key === Constants.TAB_NAMES.purchased_items) return Images.ic_items;
    return Images.tab_invoices;
  }

  handleIndexChange = (index) => {
    this.setState({ index });
    if (index === 0) {
      sendMixpanelEvent(MixpanelEvents.UPLOAD_TAB_OPENED);
    } else if (index === 1) {
      sendMixpanelEvent(MixpanelEvents.INVOICES_TAB_OPENED);
    } else if (index === 2) {
      sendMixpanelEvent(MixpanelEvents.CREDIT_REQUESTS_TAB_OPENED);
    } else if (index === 3) {
      sendMixpanelEvent(MixpanelEvents.PAYMENT_TAB_OPENED);
    } else if (index === 4) {
      sendMixpanelEvent(MixpanelEvents.ITEMS_TAB_OPENED);
    }
  };

  renderScene({ route }) {
    const { navigation, canAddCreditRequest, canUploadInvoice } = this.props;
    switch (route.key) {
      case Constants.TAB_NAMES.uploads:
        return (
          <UploadInvoiceContainer
            canUploadInvoice={canUploadInvoice}
            navigation={navigation}
          />
        );
      case Constants.TAB_NAMES.invoices:
        return (
          <ApprovalInvoices
            navigation={navigation}
          />
        );
      case Constants.TAB_NAMES.credit_request:
        return (
          <CreditRequests
            canAddCreditRequest={canAddCreditRequest}
            navigation={navigation}
          />
        );
      case Constants.TAB_NAMES.payments:
        return (
          <ApprovalPayments
            navigation={navigation}
          />
        );
      case Constants.TAB_NAMES.purchased_items:
        return (
          <AllPurchasedItemsContainer
            navigation={navigation}
          />
        );
      default:
        return (
          <ApprovalInvoices
            navigation={navigation}
          />
        );
    }
  }

  renderIcon(props) {
    const { focused, route } = props;
    return (
      <Image
        source={this.getIcon(route.key)}
        style={focused ? styles.selectedIcon : styles.unselectedIcon}
        resizeMode="contain"
      />
    );
  }

  renderLogoutDialog() {
    const { isLogoutVisible, showLogoutPopup, logout } = this.props;
    global.logoutMethod = logout;
    return (
      <Logout
        visible={isLogoutVisible}
        showLogoutPopup={showLogoutPopup}
        logout={logout}
      />
    );
  }

  render() {
    const { routes } = this.props;
    const { index } = this.state;

    return (
      <View style={{ flex: 1 }}>
        <BottomNavigation
          shifting={false}
          navigationState={{ index, routes }}
          onIndexChange={this.handleIndexChange}
          renderScene={(props) => this.renderScene(props)}
          activeColor={Colors.deepSkyBlue}
          barStyle={{ backgroundColor: Colors.white }}
          renderIcon={(props) => this.renderIcon(props)}
          onTabPress={(props) => this.onTabPress(props)}
        />
        {this.renderLogoutDialog()}
      </View>
    );
  }
}
