import React, { Component } from 'react';
import { connect } from 'react-redux';
import { loginWithToken } from '../../../actions';
import SSOLogin from '../../../components/Auth/SSOLogin';
import showAlert from '../../../utils/QubiqleAlert';

class SSOLoginContainer extends Component {
  constructor(props) {
    super(props);
    this.state = {
      submit_username: '',
      submit_password: ''
    };
  }

  // eslint-disable-next-line no-unused-vars,react/no-deprecated
  componentWillReceiveProps(nextProps, nextState) {
    if (nextProps.auth !== this.props.auth) {
      const { error } = nextProps.auth;
      if (error) {
        showAlert('Error', error);
        return;
      }

      if (nextProps.auth.isLogin) {
        this.props.navigation.navigate('LoadUserInfo');
      }
    }
  }

  render() {
    const { data } = this.props.navigation.state.params;
    const { loginWithToken } = this.props;

    return (
      <SSOLogin
        data={data}
        loginWithToken={loginWithToken}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  sso: state.sso,
  auth: state.auth
});

export default connect(
  mapStateToProps,
  { loginWithToken }
)(SSOLoginContainer);
