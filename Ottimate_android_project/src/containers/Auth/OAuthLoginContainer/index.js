import React, { Component } from 'react';
import { connect } from 'react-redux';
import OAuthLogin from '../../../components/Auth/OAuthLogin';
import { loginWithOAuthCode } from '../../../actions';
import showAlert from '../../../utils/QubiqleAlert';
import ParentView from '../../../components/qubiqle/ParentView';

class OAuthLoginContainer extends Component {
  constructor(props) {
    super(props);
    let state = {};
    if (this.props.navigation && this.props.navigation.state) {
      const { params } = this.props.navigation.state;
      if (params) {
        const { code } = params;
        if (code) {
          state = { code };
        }
      }
    }
    this.state = state;
  }

  componentDidMount(): void {
    const { code } = this.state;
    const { loginWithOAuthCode } = this.props;
    if (code) {
      loginWithOAuthCode(code, null);
    }
  }

  // eslint-disable-next-line no-unused-vars,react/no-deprecated
  componentWillReceiveProps(nextProps, nextState) {
    if (nextProps.oauth !== this.props.oauth) {
      const { error, mfa_token } = nextProps.oauth;
      if (error) {
        showAlert('Error', error);
        this.setState({ code: null });
        return;
      }

      if (mfa_token) {
        this.props.navigation.navigate('OAuthMfa');
      }

      if (nextProps.oauth.isLogin) {
        this.props.navigation.navigate('LoadUserInfo');
      }
    }
  }

  render() {
    const { loginWithOAuthCode } = this.props;
    const { code } = this.state;

    if (code) {
      return (
        <ParentView
          loading
        />
      );
    }

    return (
      <OAuthLogin
        loginWithOAuthCode={loginWithOAuthCode}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  oauth: state.oauth
});

export default connect(
  mapStateToProps,
  { loginWithOAuthCode }
)(OAuthLoginContainer);
