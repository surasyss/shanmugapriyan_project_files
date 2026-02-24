import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  loadVendors
} from '../../../actions';
import VendorPickerComponent from '../../../components/Global/VendorPickerComponent';

class VendorPickerContainer extends Component {
  // eslint-disable-next-line no-unused-vars,no-empty-pattern
  static navigationOptions = ({ navigation }) => ({
    title: 'Select Vendor'
  });

  constructor(props) {
    super(props);
    this.state = {
      searchText: ''
    };
  }

  componentDidMount() {
    this.props.loadVendors({});
  }

  onVendorSelect = (vendor) => {
    const { onSelect } = this.props.navigation.state.params;
    if (onSelect) {
      onSelect(vendor);
    }
    this.props.navigation.goBack();
  };

  loadNextPage(nextPage) {
    const { searchText } = this.state;

    let { page } = this.props.vendors;
    const { next, loading } = this.props.vendors;
    page += 1;
    if (nextPage) page = nextPage;

    const filter = { page };

    if (searchText) filter.query = searchText;
    if ((next || page === 1) && !loading) {
      this.props.loadVendors(filter);
    }
  }

  async changeSearchQuery(searchText) {
    await this.setState({ searchText });
    this.loadNextPage(1);
  }

  render() {
    const { loading, data, firstLoad } = this.props.vendors;
    const loadNextPage = this.loadNextPage.bind(this);
    const { searchText } = this.state;
    const changeSearchQuery = this.changeSearchQuery.bind(this);

    return (
      <VendorPickerComponent
        onSelect={this.onVendorSelect}
        firstLoad={firstLoad}
        loading={loading}
        vendors={data}
        loadNextPage={loadNextPage}
        searchText={searchText}
        changeSearchQuery={changeSearchQuery}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  vendors: state.vendors,
});

export default connect(
  mapStateToProps,
  {
    loadVendors
  }
)(VendorPickerContainer);
