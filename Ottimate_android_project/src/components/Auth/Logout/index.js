import React from 'react';
import Modal from 'react-native-modal';
import { View, Text, TouchableOpacity } from 'react-native';
import styles from './styles';
import Adapter from '../../../utils/Adapter';

export default class Logout extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      user: null
    };
  }

  async componentDidMount() {
    const user = await Adapter.getUser();
    this.setState({ user });
  }

  render() {
    const { visible, showLogoutPopup, logout } = this.props;
    const { user } = this.state;

    return (
      <Modal
        animationInTiming={1}
        animationOutTiming={1}
        style={{ flex: 0 }}
        transparent
        isVisible={visible}
        backdropOpacity={0.5}
        onBackdropPress={() => showLogoutPopup(false)}
        onRequestClose={() => showLogoutPopup(false)}
      >

        <View style={styles.container}>
          <View style={styles.row}>
            <View style={styles.nameIconParent}>
              <Text style={styles.nameIcon}>{user ? user.display_name[0] : ''}</Text>
            </View>
            <View style={styles.nameParent}>
              <Text style={styles.name}>{user ? user.display_name : ''}</Text>
              <Text style={styles.email}>{user ? user.email : ''}</Text>
            </View>
          </View>

          <TouchableOpacity style={styles.logoutButton} onPress={() => logout()}>
            <Text style={styles.logoutButtonText}>
              Log Out
            </Text>
          </TouchableOpacity>
        </View>
      </Modal>
    );
  }
}
