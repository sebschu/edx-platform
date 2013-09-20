(function(){

    window.Transcripts = window.Transcripts || {};


    Transcripts.Utils = (function(){

        var _getField = function(collection, field_name) {
            var model;

            if (collection && field_name) {
                model = collection.findWhere({
                    field_name: field_name
                });
            }

            return model;
        };

        // These are the types of URLs supported:
        // http://www.youtube.com/watch?v=0zM3nApSvMg&feature=feedrec_grec_index
        // http://www.youtube.com/user/IngridMichaelsonVEVO#p/a/u/1/QdK8U-VIH_o
        // http://www.youtube.com/v/0zM3nApSvMg?fs=1&amp;hl=en_US&amp;rel=0
        // http://www.youtube.com/watch?v=0zM3nApSvMg#t=0m10s
        // http://www.youtube.com/embed/0zM3nApSvMg?rel=0
        // http://www.youtube.com/watch?v=0zM3nApSvMg
        // http://youtu.be/0zM3nApSvMg
        var _youtubeParser = (function() {
            var cache = {};

            return function(url) {
                if (typeof url !== 'string') {
                    console.log('Transcripts.Utils.parseYoutubeLink');
                    console.log('TypeError: Wrong argument type.');

                    return false;
                }

                if (cache[url]) {
                    return cache[url];
                }

                var regExp = /.*(?:youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=)([^#\&\?]*).*/;
                var match = url.match(regExp);
                cache[url] = (match && match[1].length === 11) ? match[1] : void(0);

                return cache[url];
            };
        }());

        var _videoLinkParser = (function() {
            var cache = {};

            return function (url) {

                if (typeof url !== 'string') {
                    console.log('Transcripts.Utils.parseHTML5Link');
                    console.log('TypeError: Wrong argument type.');

                    return false;
                }

                if (cache[url]) {
                    return cache[url];
                }

                var link = document.createElement('a'),
                    match;

                link.href = url;
                match = link.pathname
                            .split('/')
                            .pop()
                            .match(/(.+)\.(mp4|webm)$/);

                if (match) {
                    cache[url] = {
                        video: match[1],
                        type: match[2]
                    };
                }

                return cache[url];
            };
        }());

        var _linkParser = function(url){
            var result;

            if (typeof url !== 'string') {
                console.log('Transcripts.Utils.parseLink');
                console.log('TypeError: Wrong argument type.');

                return false;
            }

            if (_youtubeParser(url)) {
                result = {
                    mode: 'youtube',
                    video: _youtubeParser(url),
                    type: 'youtube'
                };
            } else if (_videoLinkParser(url)) {
                result = $.extend({mode: 'html5'}, _videoLinkParser(url));
            } else {
                result = {
                    mode: 'incorrect'
                };
            }

            return result;
        };

        var _getYoutubeLink = function(video_id){
            return 'http://youtu.be/' + video_id;
        };

        var _syncCollections = function (fromCollection, toCollection) {
            fromCollection.each(function(m) {
                var model = toCollection.findWhere({
                        field_name: m.getFieldName()
                    });

                if (model) {
                    model.setValue(m.getDisplayValue());
                }
            });
        };

        return {
            getField: _getField,
            parseYoutubeLink: _youtubeParser,
            parseHTML5Link: _videoLinkParser,
            parseLink: _linkParser,
            getYoutubeLink: _getYoutubeLink,
            syncCollections: _syncCollections
        };
    }());


    Transcripts.Editor = Backbone.View.extend({

        tagName: 'div',

        initialize: function() {
            var metadata = this.$el.data('metadata'),
                models = this.toModels(metadata);

            this.collection = new CMS.Models.MetadataCollection(models);

            this.metadataEditor = new CMS.Views.Metadata.Editor({
                el: this.$el,
                collection: this.collection
            });
        },

        // Convert metadata JSON to List of models
        toModels: function(data) {
            var metadata = (_.isString(data)) ? JSON.parse(data) : data,
                models = [];

            for (var model in metadata){
                if (metadata.hasOwnProperty(model)) {
                    models.push(metadata[model]);
                }
            }

            return models;
        },

        syncBasicTab: function(metadataCollection) {
            var result = [],
                utils = Transcripts.Utils,
                getField = utils.getField,
                html5SourcesValue, youtubeValue, videoUrl;

            if (!metadataCollection) {
                return false;
            }

            html5SourcesValue = getField(metadataCollection, 'html5_sources')
                                    .getDisplayValue();

            youtubeValue = getField(metadataCollection, 'youtube_id_1_0')
                                    .getDisplayValue();

            videoUrl = getField(this.collection,'video_url');

            youtubeValue = (youtubeValue.length === 11)
                                ? utils.getYoutubeLink(youtubeValue)
                                : '';

            result.push(youtubeValue);
            result = result.concat(html5SourcesValue);

            videoUrl.setValue(result);
            utils.syncCollections(metadataCollection, this.collection);
        },

        syncAdvancedTab: function(metadataCollection) {
            var utils = Transcripts.Utils,
                getField = utils.getField,
                html5Sources, youtube, videoUrlValue, result;


            if (!metadataCollection) {
                return false;
            }

            html5Sources = getField(
                                metadataCollection,
                                'html5_sources'
                            );

            youtube = getField(
                                metadataCollection,
                                'youtube_id_1_0'
                            );

            videoUrlValue = getField(this.collection, 'video_url')
                                .getDisplayValue();

            result = _.groupBy(
                videoUrlValue,
                function(value) {
                    return utils.parseLink(value).mode;
                }
            );


            // TODO: CHECK result['html5']
            if (html5Sources) {
                html5Sources.setValue(result.html5 || []);
            }

            if (youtube) {
                result = (result.youtube)
                            ? utils.parseLink(result.youtube[0]).video
                            : '';

                youtube.setValue(result);
            }

            utils.syncCollections(this.collection, metadataCollection);
        }

    });


    CMS.Views.Metadata.VideoList = CMS.Views.Metadata.AbstractEditor.extend({

        events : {
            'click .setting-clear' : 'clear',
            'keypress .setting-input' : 'showClearButton',
            'change input' : 'updateModel',
            'click .collapse-setting' : 'toggleAdditional'
        },

        templateName: 'metadata-videolist-entry',
        placeholders: {
            'webm': '.webm',
            'mp4': 'http://somesite.com/video.mp4',
            'youtube': 'http://youtube.com/'
        },

        initialize: function() {
            CMS.Views.Metadata.AbstractEditor.prototype.initialize
                .apply(this, arguments);

            this.location_id = this.$el.closest('.component').data('id');

            this.$el.on(
                'input', 'input',
                _.debounce(_.bind(this.checkValidity, this), 300)
            );

            this.messanger = new Transcripts.MessageManager({
                container: this.$el
            });
        },

        getValueFromEditor: function () {
            return _.map(
                this.$el.find('.input'),
                function (ele) { return ele.value.trim(); }
            ).filter(_.identity);
        },

        setValueInEditor: function (value) {
            var list = this.$el.find('.input'),
                val = value.filter(_.identity),
                placeholders = this.getPlaceholders(val);

            for (var i = 0; i < 3; i += 1) {
                list.eq(i)
                    .val(val[i] || null)
                    .attr('placeholder', placeholders[i]);
            }

            if (value.length > 1) {
                this.openAdditional();
            } else {
                this.closeAdditional();
            }
        },

        getPlaceholders: function (value) {
            var parseLink = Transcripts.Utils.parseLink,
                placeholders = _.clone(this.placeholders),
                result = [],
                label, type;

            for (var i = 0; i < 3; i += 1) {
                type = parseLink(value[i]).type;

                if (placeholders[type]) {
                    label = placeholders[type];
                    delete placeholders[type];
                } else {
                    placeholders = _.values(placeholders);
                    label = placeholders.pop();
                }

                result.push(label);
            }

            return result;
        },

        openAdditional: function(event) {
            if (event && event.preventDefault) {
                event.preventDefault();
            }

            this.$el.find('.videolist-additional').addClass('is-visible');
        },

        closeAdditional: function(event) {
            if (event && event.preventDefault) {
                event.preventDefault();
            }

            this.$el.find('.videolist-additional').removeClass('is-visible');
        },

        toggleAdditional: function(event) {
            if (event && event.preventDefault) {
                event.preventDefault();
            }

            if (this.$el.find('.videolist-additional').hasClass('is-visible')) {
                this.closeAdditional.apply(this, arguments);
            } else {
                this.openAdditional.apply(this, arguments);
            }
        },

        checkValidity: function(event){

            if (event && event.preventDefault) {
                event.preventDefault();
            }

            var self = this,
                entry = $(event.currentTarget).val(),
                data = Transcripts.Utils.parseLink(entry);

            switch (data.mode) {
                case 'youtube':
                    this.fetchCaptions(data.video)
                        .always(function(response, statusText){
                            if (response.status === 200) {
                                self.messanger.render('found');
                            } else {
                                self.messanger.render('not_found');
                            }
                        });
                    break;

                case 'html5':

                    if (self.options.transcriptsExist) {
                        self.messanger.render('found');
                    } else {
                        self.messanger.render('not_found');
                    }
                    this.openAdditional();
                    break;
            }

            console.log(data);
        },

        fetchCaptions: function(video_id){
            var data = $.extend({id: this.location_id}, data);

            if (this.xhr && this.xhr.abort) this.xhr.abort();
            this.xhr = $.ajax({
                url: '/check_subtitles',
                data: data
            });

            return this.xhr;
        }
    });


    Transcripts.MessageManager = Backbone.View.extend({
        tagName: 'div',
        elClass: '.wrapper-transcripts-message',

        events: {
        },

        templates: {
            not_found: '#transcripts-not-found', // 0: no found on both, type: HTML5, YT (no on yt)
            found: '#transcripts-found', // 1: on edx
            on_youtube: '#transcripts-on-youtube', // 2: no found on EDX, mode: YT
            conflict:  '#transcripts-conflict', // 3: add YT to existing HTML5 with subs, type: YT
            uploaded:  '#transcripts-uploaded', // when subtitles was uploaded, type: HTML5
            not_updated: '#transcripts-not-updated' // change source, type: HTML5
        },

        initialize: function () {
            var container = this.options.container;

            this.fileUploader = new Transcripts.FileUploader({
                el: container,
                messanger: this
            });
        },

        render: function (template) {
            var tpl = $(this.templates[template]).text();

            if(!tpl) {
                console.error('Couldn\'t load Transcripts status template');
            }
            this.template = _.template(tpl);
            this.options.container.find(this.elClass).html(this.template());
            this.fileUploader.render();
        }
    });


    Transcripts.FileUploader = Backbone.View.extend({
        invisibleClass: 'is-invisible',
        validFileExtensions: ['srt'],

        ERRORS: {
            'file-type': 'Please select a file in .srt format.'
        },

        events: {
            'change .file-input': 'changeHadler',
            'click .setting-upload': 'clickHandler'
        },

        uploadTpl: '#transcripts-file-upload',
        initialize: function () {
            _.bindAll(this);

            this.component_id = this.$el.closest('.component').data('id');
            this.file = false;
            this.render();
        },

        render: function () {
            var tpl = $(this.uploadTpl).text(),
                tplContainer = this.$el.find('.transcripts-file-uploader');

            if (tplContainer) {
                if(!tpl) {
                    console.error('Couldn\'t load Transcripts File Upload template');
                }
                this.template = _.template(tpl);

                tplContainer.html(this.template({
                    ext: this.validFileExtensions,
                    component_id: this.component_id
                }));

                this.$statusBar = this.$el.find('.transcripts-message-status');
                this.$form = this.$el.find('.file-chooser');
                this.$input = this.$form.find('.file-input');
                this.$progress = this.$el.find('.progress-fill');
                this.$error = this.$el.find('.transcripts-error-message');
            }
        },

        upload: function () {
            if (!this.file){
                return;
            }

            this.$form.ajaxSubmit({
                beforeSend: this.xhrResetProgressBar,
                uploadProgress: this.xhrProgressHandler,
                complete: this.xhrCompleteHandler
            });
        },

        showError: function (error, customError) {
            var err = (customError) ? error : this.ERRORS[error];

            if (err) {
                this.$error
                    .html(gettext(err))
                    .removeClass(this.invisibleClass);
            }
        },

        hideError: function () {
            this.$error
                .addClass(this.invisibleClass);
        },

        clickHandler: function (event) {
            event.preventDefault();

            this.$input
                .val(null)
                .trigger('click');
        },

        uploadHadler: function (event) {
            event.preventDefault();

            this.upload();
        },

        changeHadler: function (event) {
            event.preventDefault();

            this.hideError();
            this.file = this.$input.get(0).files[0];

            if (this.checkExtValidity(this.file)) {
                this.upload();
            } else {
                this.showError('file-type');
            }
        },

        checkExtValidity: function (file) {
            var fileExtension = file.name
                                    .split('.')
                                    .pop()
                                    .toLowerCase();

            if ($.inArray(fileExtension, this.validFileExtensions) !== -1) {
                return true;
            }

            return false;
        },

        xhrResetProgressBar: function () {
            var percentVal = '0%';

            this.$progress
                .width(percentVal)
                .html(percentVal)
                .removeClass(this.invisibleClass);
        },

        xhrProgressHandler: function (event, position, total, percentComplete) {
            var percentVal = percentComplete + '%';

            this.$progress
                .width(percentVal)
                .html(percentVal);
        },

        xhrCompleteHandler: function (xhr) {
            var resp = JSON.parse(xhr.responseText);

            this.$progress
                .addClass(this.invisibleClass);

            if (xhr.status === 200 && resp.success) {
                this.options.messanger.render('uploaded');
            } else {
                // TODO Retrieve error form server
                console.log('Error: Uploading failed.');
                if (resp.error) {
                    this.showError(resp.error, true);
                }
            }
        }
    });


}(this));
