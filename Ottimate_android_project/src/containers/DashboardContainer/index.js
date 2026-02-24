import React, { Component } from 'react';
import { connect } from 'react-redux';
import { TouchableOpacity, Image } from 'react-native';
import {
  loadUserInfo, loadRestaurants, loadCompanies, logout
} from '../../actions';
import Dashboard from '../../components/Dashboard';
import styles from './styles';
import Images from '../../styles/Images';
import { MixpanelEvents, removeMixpanelUser, sendMixpanelEvent } from '../../utils/mixpanel/MixPanelAdapter';
import Constants from '../../utils/Constants';

class DashboardContainer extends Component {
    static navigationOptions = ({ navigation }) => {
      let title = 'Upload';
      let showLogoutPopup = null;
      const { params } = navigation.state;
      if (params) {
        title = params.title;
        showLogoutPopup = params.showLogoutPopup;
      }

      return {
        title,
        headerLeft: () => (
          <TouchableOpacity onPress={() => showLogoutPopup(true)}>
            <Image
              source={Images.user}
              style={styles.headerIcon}
              resizeMode="contain"
            />
          </TouchableOpacity>
        ),
        headerBackTitle: '',
      };
    };

    constructor(props) {
      super(props);
      this.state = {
        isLogoutVisible: false,
      };
    }

    async componentDidMount() {
      this.props.navigation.setParams({
        title: 'Upload',
        showLogoutPopup: this.showLogoutPopup
      });
      this.props.loadRestaurants();
      this.props.loadCompanies();
    }

    setTitle(title) {
      this.props.navigation.setParams({ title });
    }

    getTabs() {
      const { showPayments, showCreditRequest, showItems } = this.props.userInfo;
      const tabs = [
        { key: 'uploads', title: 'Uploads' },
        { key: 'invoices', title: 'Invoices' },
      ];
      if (showCreditRequest) {
        tabs.push({ key: 'credit_requests', title: 'Credits' });
      }
      if (showPayments) {
        tabs.push({ key: 'payments', title: 'Payments' });
      }
      if (showItems) {
        tabs.push({ key: 'purchased_items', title: 'Items' });
      }
      return tabs;
    }

    showLogoutPopup = (isLogoutVisible) => {
      this.setState({
        isLogoutVisible
      });
    };

    async logout() {
      await sendMixpanelEvent(MixpanelEvents.USER_LOGGED_OUT);
      await removeMixpanelUser();
      this.props.logout();
      this.props.navigation.navigate(Constants.ROOT_LOGIN_PAGE);
    }

    render() {
      const setTitle = this.setTitle.bind(this);
      const logout = this.logout.bind(this);
      const { isLogoutVisible } = this.state;
      const { navigation } = this.props;
      const { canAddCreditRequest, canUploadInvoice } = this.props.userInfo;

      return (
        <Dashboard
          setTitle={setTitle}
          isLogoutVisible={isLogoutVisible}
          showLogoutPopup={this.showLogoutPopup}
          logout={logout}
          navigation={navigation}
          routes={this.getTabs()}
          canAddCreditRequest={canAddCreditRequest}
          canUploadInvoice={canUploadInvoice}
        />
      );
    }
}

const mapStateToProps = (state) => ({
  userInfo: state.userInfo
});

export default connect(mapStateToProps, {
  loadUserInfo, loadRestaurants, loadCompanies, logout
})(DashboardContainer);
