import React, { Component } from 'react';
import { connect } from 'react-redux';
import { loginMfa, resendMfa } from '../../../actions';
import showAlert from '../../../utils/QubiqleAlert';
import Mfa from '../../../components/Auth/Mfa';

class MfaContainer extends Component {
  // eslint-disable-next-line no-unused-vars,react/no-deprecated
  componentWillReceiveProps(nextProps, nextState) {
    if (nextProps.mfa !== this.props.mfa) {
      const { error } = nextProps.mfa;
      if (error) {
        showAlert('Unable to Complete Sign-in', error);
        return;
      }

      if (nextProps.mfa.isLogin) {
        this.props.navigation.navigate('LoadUserInfo');
      }
    }
  }

  login = (code) => {
    if (!code) {
      showAlert('Error', 'Code is required');
      return;
    }
    this.props.loginMfa(this.props.auth.mfa_token, code);
  };

  goBack = () => {
    this.props.navigation.goBack();
  };

  resendCode = () => {
    const { username, password } = this.props.navigation.state.params;
    this.props.resendMfa({ username, password });
  };

  render() {
    const { loading } = this.props.mfa;

    return (
      <Mfa
        hoverLoading={loading}
        login={this.login}
        goBack={this.goBack}
        resendCode={this.resendCode}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  mfa: state.mfa,
  auth: state.auth
});

export default connect(
  mapStateToProps,
  { loginMfa, resendMfa }
)(MfaContainer);
