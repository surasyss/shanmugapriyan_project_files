import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  loadPendingApprovalInvoices, resetPendingApprovalInvoices, loadInvoiceDetails, setCurrentInvoice, loadRestaurantUsers
} from '../../../actions';
import PendingApproval from '../../../components/Invoices/PendingApproval';
import { MixpanelEvents, sendMixpanelEvent } from '../../../utils/mixpanel/MixPanelAdapter';

class PendingApprovalContainer extends Component {
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
    this.props.loadPendingApprovalInvoices({});
  }

  async setFilter(filters) {
    await this.setState({ filters });
    await this.props.resetPendingApprovalInvoices();
    this.loadNextPage(1);
    sendMixpanelEvent(MixpanelEvents.INVOICES_FILTERED, { filters });
  }

  loadNextPage(nextPage) {
    const { searchText, filters } = this.state;

    let { page } = this.props.pendingInvoices;
    const { next, loading } = this.props.pendingInvoices;
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
      this.props.loadPendingApprovalInvoices(filter);
    }
  }

  goToInvoiceDetail(index) {
    const invoice = this.props.pendingInvoices.data[index];
    sendMixpanelEvent(MixpanelEvents.INVOICE_OPENED, { invoice });
    this.props.setCurrentInvoice(null);
    this.props.loadInvoiceDetails(invoice.id);
    this.props.loadRestaurantUsers(invoice.restaurant);
    this.props.navigation.navigate('InvoiceDetail', {
      type: 'pending',
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
    const { loading, data, firstLoad } = this.props.pendingInvoices;
    const { canAccessDashboard } = this.props.userInfo;
    const loadNextPage = this.loadNextPage.bind(this);
    const goToInvoiceDetail = this.goToInvoiceDetail.bind(this);
    // eslint-disable-next-line no-shadow
    const { resetPendingApprovalInvoices } = this.props;
    const { searchText, isSearchVisible, isFilterVisible } = this.state;
    const openSearch = this.openSearch.bind(this);
    const changeSearchQuery = this.changeSearchQuery.bind(this);
    const openFilter = this.openFilter.bind(this);
    const setFilter = this.setFilter.bind(this);
    const { filters } = this.state;

    return (
      <PendingApproval
        firstLoad={firstLoad}
        loading={loading}
        invoices={data}
        loadNextPage={loadNextPage}
        goToInvoiceDetail={goToInvoiceDetail}
        onSearchClick={resetPendingApprovalInvoices}
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
  pendingInvoices: state.pendingInvoices,
  userInfo: state.userInfo,
});

export default connect(
  mapStateToProps,
  {
    loadPendingApprovalInvoices, resetPendingApprovalInvoices, loadInvoiceDetails, setCurrentInvoice, loadRestaurantUsers
  }
)(PendingApprovalContainer);
