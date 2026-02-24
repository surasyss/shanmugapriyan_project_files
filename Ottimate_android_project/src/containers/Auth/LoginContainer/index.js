import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  loginUser, loginWithToken, checkSSOUser, resetSSOData,
} from '../../../actions';
import Login from '../../../components/Auth/Login';
import showAlert from '../../../utils/QubiqleAlert';
import Constants from '../../../utils/Constants';

class LoginContainer extends Component {
  constructor(props) {
    super(props);
    this.state = {
      submit_username: '',
      submit_password: '',
      isSSOLogin: false
    };
  }

  componentDidMount(): void {
    if (this.props.navigation && this.props.navigation.state) {
      const { params } = this.props.navigation.state;
      if (params) {
        const { access_token } = params;
        if (access_token) {
          this.props.loginWithToken(access_token);
        }
      }
    }
  }

  // eslint-disable-next-line no-unused-vars,react/no-deprecated
  componentWillReceiveProps(nextProps, nextState) {
    if (nextProps.sso !== this.props.sso) {
      const { data, error } = nextProps.sso;

      if (error) {
        showAlert(Constants.INCOMPLETE_SIGNIN, Constants.ERROR_COMMON);
        this.props.resetSSOData();
        return;
      }

      if (data) {
        if (!this.state.isSSOLogin && data.is_sso) {
          showAlert(Constants.ERROR, Constants.SSO_USER_ERROR);
          this.props.resetSSOData();
          return;
        }

        if (this.state.isSSOLogin && data.is_sso === false) {
          showAlert(Constants.ERROR, Constants.NON_SSO_USER_ERROR);
          this.props.resetSSOData();
          return;
        }

        if (this.state.isSSOLogin && data.is_sso) {
          this.props.navigation.navigate('SSOLogin', { data });
        } else {
          this.props.loginUser({ username: this.state.submit_username, password: this.state.submit_password });
        }
      }
    }

    if (nextProps.auth !== this.props.auth) {
      const { error, mfa_token } = nextProps.auth;
      if (error) {
        showAlert(Constants.ERROR, error);
        return;
      }

      if (mfa_token) {
        const { submit_username, submit_password } = this.state;
        this.props.navigation.navigate('Mfa', { username: submit_username, password: submit_password });
      }

      if (nextProps.auth.isLogin) {
        this.props.navigation.navigate('LoadUserInfo');
      }
    }
  }

  login(username, password) {
    if (this.state.isSSOLogin && !username) {
      showAlert(Constants.ERROR, Constants.EMAIL_REQUIRED);
      return;
    }

    if (!this.state.isSSOLogin) {
      if (!username) {
        showAlert(Constants.ERROR, Constants.USERNAME_REQUIRED);
        return;
      }
      if (!password) {
        showAlert(Constants.ERROR, Constants.PASSWORD_REQUIRED);
        return;
      }
      this.setState({
        submit_username: username,
        submit_password: password
      });
    }
    this.props.checkSSOUser(username);
  }

  toggleLogin() {
    this.setState((previousState) => ({
      isSSOLogin: !previousState.isSSOLogin
    }));
  }

  render() {
    const login = this.login.bind(this);
    const { loading } = this.props.auth;
    const { data } = this.props.sso;
    const { isSSOLogin } = this.state;

    return (
      <Login
        hoverLoading={loading}
        login={login}
        data={data}
        toggleLogin={this.toggleLogin.bind(this)}
        isSSOLogin={isSSOLogin}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  auth: state.auth,
  sso: state.sso,
});

export default connect(
  mapStateToProps,
  {
    loginUser, loginWithToken, checkSSOUser, resetSSOData
  }
)(LoginContainer);
