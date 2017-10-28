from flask_appbuilder import IndexView


class SiteIndexView(IndexView):
    index_template = 'index.html'
