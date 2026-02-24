import React, { Component } from 'react';
import {
  View, Image, Platform
} from 'react-native';
import styles from './styles';
import Images from '../../../styles/Images';
import ParentView from '../../qubiqle/ParentView';
import Spinner from '../../qubiqle/Spinner';
import Colors from '../../../styles/Colors';

export default class LoadUserInfo extends Component {
  renderHeader() {
    return (
      <View style={styles.logoParent}>
        <Image style={styles.logo} source={Images.loginScreenLogo} />
      </View>
    );
  }

  renderLoader() {
    return (
      <Spinner
        visible
        color={Platform.OS === 'ios' ? Colors.white : Colors.primary}
        textContent="Loading user details"
        textStyle={styles.loadingText}
      />
    );
  }

  render() {
    const { hoverLoading } = this.props;
    return (
      <ParentView style={styles.container} hoverLoading={hoverLoading}>
        {this.renderHeader()}
        {this.renderLoader()}
      </ParentView>
    );
  }
}
