import React, { Component } from 'react';
import { connect } from 'react-redux';
import {
  loadCategories
} from '../../../actions';
import CategoryPickerComponent from '../../../components/Global/CategoryPickerComponent';

class CategoryPickerContainer extends Component {
  // eslint-disable-next-line no-unused-vars,no-empty-pattern
  static navigationOptions = ({ navigation }) => ({
    title: 'Select Category'
  });

  constructor(props) {
    super(props);
    this.state = {
      searchText: ''
    };
  }

  componentDidMount() {
    const { parent } = this.props.navigation.state.params;
    const filter = {};
    if (parent) {
      filter.parent = parent.id;
    }
    this.props.loadCategories(filter);
  }

  onCategorySelect = (category) => {
    const { onSelect } = this.props.navigation.state.params;
    if (onSelect) {
      onSelect(category);
    }
    this.props.navigation.goBack();
  };

  loadNextPage(nextPage) {
    const { searchText } = this.state;

    let { page } = this.props.categories;
    const { next, loading } = this.props.categories;
    page += 1;
    if (nextPage) page = nextPage;

    const filter = { page };

    const { parent } = this.props.navigation.state.params;
    if (parent) {
      filter.parent = parent.id;
    }

    if (searchText) filter.query = searchText;
    if ((next || page === 1) && !loading) {
      this.props.loadCategories(filter);
    }
  }

  async changeSearchQuery(searchText) {
    await this.setState({ searchText });
    this.loadNextPage(1);
  }

  render() {
    const { loading, data, firstLoad } = this.props.categories;
    const loadNextPage = this.loadNextPage.bind(this);
    const { searchText } = this.state;
    const changeSearchQuery = this.changeSearchQuery.bind(this);

    return (
      <CategoryPickerComponent
        onSelect={this.onCategorySelect}
        firstLoad={firstLoad}
        loading={loading}
        categories={data}
        loadNextPage={loadNextPage}
        searchText={searchText}
        changeSearchQuery={changeSearchQuery}
      />
    );
  }
}

const mapStateToProps = (state) => ({
  categories: state.categories,
});

export default connect(
  mapStateToProps,
  {
    loadCategories
  }
)(CategoryPickerContainer);
