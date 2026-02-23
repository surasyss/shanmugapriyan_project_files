import React, { Component } from 'react';
import { connect } from 'react-redux';
import { loadUserInfo, loadRestaurants, loadCompanies } from '../../../actions';
import LoadUserInfo from '../../../components/Auth/LoadUserInfo';

class LoadUserInfoContainer extends Component {
  componentDidMount() {
    this.props.loadUserInfo();
    this.props.loadRestaurants();
    this.props.loadCompanies();
  }

  // eslint-disable-next-line no-unused-vars,react/no-deprecated
  componentWillReceiveProps(nextProps, nextState) {
    if (!nextProps.userInfo.loadingUserInfo && this.props.userInfo.loadingUserInfo) {
      this.props.navigation.navigate('App');
    }
  }

  render() {
    return (
      <LoadUserInfo />
    );
  }
}

const mapStateToProps = (state) => ({
  userInfo: state.userInfo,
});

export default connect(
  mapStateToProps,
  { loadUserInfo, loadRestaurants, loadCompanies }
)(LoadUserInfoContainer);
