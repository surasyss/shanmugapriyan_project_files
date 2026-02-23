import React, { Component } from 'react';
import { BackHandler, Image, View } from 'react-native';
import branch from 'react-native-branch';
import { startUpdateFlow } from '@gurukumparan/react-native-android-inapp-updates';
import VersionCheck from 'react-native-version-check';
import Images from '../../../styles/Images';
import styles from './styles';
import Adapter from '../../../utils/Adapter';
import PendingUploadAdapter from '../../../utils/PendingUploadAdapter';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';
import Constants from '../../../utils/Constants';
import PendingTransactionUploadAdapter from '../../../utils/PendingTransactionUploadAdapter';
import Urls from '../../../api/urls';
import api from '../../../api';

export default class Splash extends Component {
  async componentDidMount() {
    await PendingUploadAdapter.deleteCreatedInvoice();
    await PendingTransactionUploadAdapter.deleteCreatedTransactionReceipt();
    await sendMixpanelEvent(MixpanelEvents.APP_LAUNCHED);

    branch.skipCachedEvents();
    this.subscribeFromBranch = branch.subscribe(({ error, params }) => {
      if (error || !params || !params['+clicked_branch_link']) {
        this.checkUpdate();
        return;
      }
      const { access_token, code } = params;
      if (params['+clicked_branch_link'] && access_token) {
        this.props.navigation.navigate(Constants.ROOT_LOGIN_PAGE, { access_token });
        return;
      }
      if (params['+clicked_branch_link'] && code) {
        this.props.navigation.navigate(Constants.ROOT_LOGIN_PAGE, { code });
        return;
      }
      this.checkUpdate();
    });

    branch.getLatestReferringParams()
      .then((latestParams) => {
        if (!latestParams || !latestParams['+clicked_branch_link']) {
          this.checkUpdate();
          return;
        }
        const { access_token, code } = latestParams;
        if (latestParams['+clicked_branch_link'] && access_token) {
          this.props.navigation.navigate(Constants.ROOT_LOGIN_PAGE, { access_token });
          return;
        }
        if (latestParams['+clicked_branch_link'] && code) {
          this.props.navigation.navigate(Constants.ROOT_LOGIN_PAGE, { code });
          return;
        }
        this.checkUpdate();
      })
      .catch(() => {
        this.checkUpdate();
      });

    this.timeoutHandle = setTimeout(() => {
      this.checkUpdate();
    }, 5000);
  }

  componentWillUnmount() {
    if (this.timeoutHandle) {
      clearTimeout(this.timeoutHandle);
      this.timeoutHandle = null;
    }
    if (this.subscribeFromBranch) {
      this.subscribeFromBranch();
      this.subscribeFromBranch = null;
    }
  }

  async forceUpdate(version) {
    const {
      data
    } = await api({
      method: 'GET',
      url: Urls.FORCE_UPDATE + version,
    });

    const { force_update } = data;
    return force_update;
  }

  async checkUpdate() {
    VersionCheck.getLatestVersion().then((version) => {
      this.forceUpdate(version).then((force) => {
        if (force) {
          startUpdateFlow('immediate').then((result) => {
            if (result === 'Successful') {
              this.openApp();
            } else {
              BackHandler.exitApp();
            }
          }).catch(() => { this.openApp(); });
        } else {
          this.openApp();
        }
      });
    });
  }

  async openApp() {
    // Start the Pushy service
    try {
      const user = await Adapter.getToken();
      if (user) {
        this.props.navigation.navigate('LoadUserInfo');
      } else {
        this.props.navigation.navigate(Constants.ROOT_LOGIN_PAGE);
      }
    } catch (e) {

    }
  }

  render() {
    return (
      <View style={styles.container}>
        <Image
          style={styles.logo}
          resizeMode="contain"
          source={Images.splashLogo}
        />
      </View>
    );
  }
}
