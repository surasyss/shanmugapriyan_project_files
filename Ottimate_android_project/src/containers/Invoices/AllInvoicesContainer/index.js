import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  loadAllInvoices, resetAllInvoices, loadInvoiceDetails, setCurrentInvoice, loadRestaurantUsers
} from '../../../actions';
import AllInvoices from '../../../components/Invoices/AllInvoices';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';

class AllInvoicesContainer extends Component {
  constructor(props) {
    super(props);
    this.state = {
      searchText: '',
      isSearchVisible: false,
      isFilterVisible: false,
      filters: {}
    };
  }

  componentDidMount() {
    this.props.loadAllInvoices({});
  }

  async setFilter(filters) {
    await this.setState({ filters });
    await this.props.resetAllInvoices();
    this.loadNextPage(1);
    sendMixpanelEvent(MixpanelEvents.INVOICES_FILTERED, { filters });
  }

  loadNextPage(nextPage) {
    const { searchText, filters } = this.state;

    let { page } = this.props.allInvoices;
    const { next, loading } = this.props.allInvoices;
    page += 1;

    const {
      restaurant, vendor, company, date_range, date_type
    } = filters;

    if (nextPage) page = nextPage;

    const filter = { page };

    if (searchText) filter.query = searchText;
    if (restaurant) filter.restaurant = restaurant.id;
    if (vendor) filter.vendor = vendor.id;
    if (company) filter.company = company.id;
    if (date_range) {
      let type = 'date';
      if (date_type) type = date_type.key;
      const { start, end } = date_range;
      filter[`${type}__gte`] = start;
      filter[`${type}__lte`] = end;
    }

    if ((next || page === 1) && !loading) {
      this.props.loadAllInvoices(filter);
    }
  }

  goToInvoiceDetail(index) {
    const invoice = this.props.allInvoices.data[index];
    sendMixpanelEvent(MixpanelEvents.INVOICE_OPENED, { invoice });
    this.props.setCurrentInvoice(null);
    this.props.loadInvoiceDetails(invoice.id);
    this.props.loadRestaurantUsers(invoice.restaurant);
    this.props.navigation.navigate('InvoiceDetail', {
      type: 'all',
      index
    });
  }

  openSearch(isSearchVisible) {
    this.setState({ isSearchVisible });
  }

  changeSearchQuery(searchText) {
    this.setState({ searchText });
  }

  openFilter(isFilterVisible) {
    this.setState({ isFilterVisible });
  }

  render() {
    const { loading, data, firstLoad } = this.props.allInvoices;
    const { canAccessDashboard } = this.props.userInfo;
    const loadNextPage = this.loadNextPage.bind(this);
    const goToInvoiceDetail = this.goToInvoiceDetail.bind(this);
    const { resetAllInvoices } = this.props;
    const { searchText, isSearchVisible, isFilterVisible } = this.state;
    const openSearch = this.openSearch.bind(this);
    const changeSearchQuery = this.changeSearchQuery.bind(this);
    const openFilter = this.openFilter.bind(this);
    const setFilter = this.setFilter.bind(this);
    const { filters } = this.state;

    return (
      <AllInvoices
        firstLoad={firstLoad}
        loading={loading}
        invoices={data}
        loadNextPage={loadNextPage}
        goToInvoiceDetail={goToInvoiceDetail}
        onSearchClick={resetAllInvoices}
        searchText={searchText}
        isSearchVisible={isSearchVisible}
        openSearch={openSearch}
        changeSearchQuery={changeSearchQuery}
        isFilterVisible={isFilterVisible}
        openFilter={openFilter}
        setFilter={setFilter}
        filters={filters}
        canAccessDashboard={canAccessDashboard}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  allInvoices: state.allInvoices,
  userInfo: state.userInfo
});

export default connect(
  mapStateToProps,
  {
    loadAllInvoices, resetAllInvoices, loadInvoiceDetails, setCurrentInvoice, loadRestaurantUsers
  }
)(AllInvoicesContainer);
