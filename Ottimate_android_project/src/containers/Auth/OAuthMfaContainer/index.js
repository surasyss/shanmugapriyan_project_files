import React, { Component } from 'react';
import { connect } from 'react-redux';
import { loginWithOAuthMfa } from '../../../actions';
import showAlert from '../../../utils/QubiqleAlert';
import OAuthMfa from '../../../components/Auth/OAuthMfa';

class OAuthMfaContainer extends Component {
  // eslint-disable-next-line no-unused-vars,react/no-deprecated
  componentWillReceiveProps(nextProps, nextState) {
    if (nextProps.oauthMfa !== this.props.oauthMfa) {
      const { error } = nextProps.oauthMfa;
      if (error) {
        showAlert('Unable to Complete Sign-in', error);
        return;
      }

      if (nextProps.oauthMfa.isLogin) {
        this.props.navigation.navigate('LoadUserInfo');
      }
    }
  }

  login = (code) => {
    if (!code) {
      showAlert('Error', 'Code is required');
      return;
    }
    this.props.loginWithOAuthMfa(this.props.oauth.mfa_token, code);
  };

  goBack = () => {
    this.props.navigation.goBack();
  };

  resendCode = () => {

  };

  render() {
    const { loading } = this.props.oauthMfa;

    return (
      <OAuthMfa
        hoverLoading={loading}
        login={this.login}
        goBack={this.goBack}
        resendCode={this.resendCode}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  oauthMfa: state.oauthMfa,
  oauth: state.oauth
});

export default connect(
  mapStateToProps,
  { loginWithOAuthMfa }
)(OAuthMfaContainer);
