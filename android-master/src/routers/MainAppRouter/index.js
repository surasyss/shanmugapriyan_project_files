import React, { Component } from 'react';
import {
  Image, TouchableOpacity, Text, View
} from 'react-native';
import { withNavigation } from 'react-navigation';
import { connect } from 'react-redux';
import styles from '../SwitchNavigator/styles';
import RBSheet from '../../components/qubiqle/RBSheet';
import { mainNavigatorTabs } from '../SwitchNavigator';
import Logout from '../../components/Auth/Logout';
import { MixpanelEvents, removeMixpanelUser, sendMixpanelEvent } from '../../utils/mixpanel/MixPanelAdapter';
import { logout } from '../../actions';

class MainAppRoute extends Component {
  constructor(props) {
    super(props);
    this.state = {
      bottomTabs: [],
      currentTab: 'uploads',
      isLogoutVisible: false,
    };
  }

  componentDidMount() {
    const { tabs } = this.props.userInfo;
    const bottomTabs = [];
    tabs.forEach((tab) => {
      bottomTabs.push({ ...mainNavigatorTabs[tab], tab });
    });
    this.setState({ bottomTabs });
  }

  navigateFromMoreSheet = (screen) => {
    let navigationRoute = null;
    if (screen === 'CreditsStack') {
      navigationRoute = 'CreditRequests';
    } else if (screen === 'TransactionsStack') {
      navigationRoute = 'Transactions';
    }
    this.props.navigation.navigate(navigationRoute);
  };

  handleTabPress = (bottomTab) => {
    const { key, tab } = bottomTab;
    this.setState({ currentTab: tab });
    if (key === 'MoreStack') {
      this.RBSheet.open();
      return;
    }
    this.props.navigation.navigate(key);
  };

  showLogoutPopup = (isLogoutVisible) => {
    this.setState({
      isLogoutVisible
    });
  };

  logoutMethod = async () => {
    await sendMixpanelEvent(MixpanelEvents.USER_LOGGED_OUT);
    await removeMixpanelUser();
    this.props.logout();
    this.props.navigation.navigate('Auth');
  }

  renderLogoutDialog() {
    const { isLogoutVisible } = this.state;
    global.logoutMethod = this.logoutMethod;
    return (
      <Logout
        ref={() => {
          global.showLogout = this.showLogoutPopup;
        }}
        visible={isLogoutVisible}
        showLogoutPopup={this.showLogoutPopup}
        logout={this.logoutMethod}
      />
    );
  }

  renderMoreSheet() {
    const { moreTabs } = this.props.userInfo;
    return (
      <RBSheet
        ref={(ref) => {
          this.RBSheet = ref;
        }}
        key="renderMoreSheet"
        closeOnDragDown
        height={300}
        openDuration={350}
        closeDuration={300}
      >
        {moreTabs.map((tab) => {
          const { key, label, icon } = mainNavigatorTabs[tab];
          return (
            <TouchableOpacity
              key={key}
              style={styles.listButton}
              onPress={() => {
                this.RBSheet.close();
                this.navigateFromMoreSheet(key);
              }}
            >
              <Image source={icon} style={styles.listIcon} />
              <Text style={styles.listLabel}>{label}</Text>
            </TouchableOpacity>
          );
        })}
      </RBSheet>
    );
  }

  render() {
    const { bottomTabs, currentTab } = this.state;
    let tabFlexValue = 1;
    if (bottomTabs.length !== 0) {
      tabFlexValue = 1 / bottomTabs.length;
    }
    return (
      <View key="renderMain" style={styles.bottomTabs}>
        {
          bottomTabs.map((bottomTab) => {
            const {
              icon, key, label, tab
            } = bottomTab;
            return (
              <TouchableOpacity
                style={{ flex: tabFlexValue, ...styles.bottomTab }}
                key={key}
                onPress={() => this.handleTabPress(bottomTab)}
              >
                <Image
                  resizeMode="contain"
                  source={icon}
                  style={currentTab === tab ? styles.selectedIcon : styles.unselectedIcon}
                />
                <Text style={currentTab === tab ? styles.selectedTabText : styles.unselectedTabText}>
                  {label}
                </Text>
              </TouchableOpacity>
            );
          })
        }
        {this.renderMoreSheet()}
        {this.renderLogoutDialog()}
      </View>
    );
  }
}

const mapStateToProps = (state) => ({
  userInfo: state.userInfo,
});

export default withNavigation(connect(
  mapStateToProps,
  { logout }
)(MainAppRoute));
